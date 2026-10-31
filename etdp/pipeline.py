"""Main loop (Algorithm 1): runs the steps, with a checkpoint after every step and resume support."""

from __future__ import annotations

import json
import logging
import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Optional

from .config import AppConfig, InputSpec
from .context import Context
from .documents import TextStore, Tokenizer
from .embeddings import Embedder, create_embedder
from .export import write_outputs
from .llm import BudgetExceeded, LLMClient, create_llm
from .models import RunState
from .sources import FullTextFetcher, SearchProvider, WebSearch, create_scholarly, create_web
from .steps import STEPS

logger = logging.getLogger("etdp")
STATE_FILE, CONFIG_FILE = "state.json", "config.json"
_TAG = "_etdp_handler"


def setup_logging(run_dir: Path) -> None:
    root = logging.getLogger("etdp")
    for h in [h for h in root.handlers if getattr(h, _TAG, False)]:
        root.removeHandler(h)
        h.close()
    root.setLevel(logging.DEBUG)
    fh = logging.FileHandler(run_dir / "run.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("%(levelname)s %(message)s"))
    try:
        sys.stderr.reconfigure(errors="backslashreplace")
    except (AttributeError, ValueError):
        pass
    for h in (fh, ch):
        setattr(h, _TAG, True)
        root.addHandler(h)
    root.propagate = False


class Pipeline:
    def __init__(self, cfg: AppConfig, state: RunState, run_dir: Path, *, llm: Optional[LLMClient] = None,
                 embedder: Optional[Embedder] = None, scholarly: Optional[SearchProvider] = None,
                 fetcher: Optional[FullTextFetcher] = None, web: Optional[WebSearch] = None,
                 tokenizer: Optional[Tokenizer] = None) -> None:
        self.cfg, self.state, self.run_dir = cfg, state, Path(run_dir)
        self.llm = llm or create_llm(cfg.llm, token_budget=cfg.limits.max_tokens_budget, log_prompts=cfg.output.log_prompts)
        self.llm.tokens_used = state.tokens_used
        self.llm.token_budget = cfg.limits.max_tokens_budget
        self.llm.tokens_by_task = dict(state.tokens_by_task)
        self.ctx = Context(cfg=cfg, state=state, llm=self.llm, embedder=embedder or create_embedder(cfg.embeddings),
                           scholarly=scholarly or create_scholarly(cfg.scholarly),
                           fetcher=fetcher or FullTextFetcher(cfg.scholarly, cfg.documents.min_fulltext_chars),
                           web=web or create_web(cfg.web, cfg.documents.max_page_chars),
                           store=TextStore(self.run_dir), tokenizer=tokenizer or Tokenizer(cfg.documents.tokenizer),
                           run_dir=self.run_dir)

    @classmethod
    def create(cls, cfg: AppConfig, inp: InputSpec, output_dir: Optional[str] = None, run_id: Optional[str] = None,
               **services) -> "Pipeline":
        run_id = run_id or datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
        run_dir = Path(output_dir or cfg.output.dir) / run_id
        if (run_dir / STATE_FILE).exists():
            raise FileExistsError(f"run {run_id} already exists; use 'resume'")
        run_dir.mkdir(parents=True, exist_ok=True)
        (run_dir / CONFIG_FILE).write_text(cfg.model_dump_json(indent=2), encoding="utf-8")
        setup_logging(run_dir)
        pipe = cls(cfg, RunState(run_id=run_id, input=inp), run_dir, **services)
        pipe.save()
        return pipe

    @classmethod
    def resume(cls, run_id: str, output_dir: Optional[str] = None, cfg: Optional[AppConfig] = None,
               **services) -> "Pipeline":
        run_dir = Path(output_dir or (cfg.output.dir if cfg else "output")) / run_id
        if not (run_dir / STATE_FILE).exists():
            raise FileNotFoundError(f"no checkpoint in {run_dir}")
        cfg = cfg or AppConfig.model_validate(json.loads((run_dir / CONFIG_FILE).read_text(encoding="utf-8")))
        setup_logging(run_dir)
        state = RunState.model_validate_json((run_dir / STATE_FILE).read_text(encoding="utf-8"))
        if state.next_step != "done" and state.status in ("failed", "budget_exhausted"):
            state.status, state.message = "running", ""
        logger.info("resuming run %s at step %s", run_id, state.next_step)
        return cls(cfg, state, run_dir, **services)

    def save(self) -> None:
        st = self.state
        st.tokens_used, st.tokens_by_task = self.llm.tokens_used, dict(self.llm.tokens_by_task)
        fd, tmp = tempfile.mkstemp(dir=self.run_dir, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(st.model_dump_json(indent=1))
        os.replace(tmp, self.run_dir / STATE_FILE)

    def run(self) -> RunState:
        st = self.state
        try:
            while st.next_step != "done":
                step = st.next_step
                logger.info("--- step %s ---", step)
                before = self.llm.tokens_used
                STEPS[step](self.ctx)
                spent = self.llm.tokens_used - before
                st.tokens_by_step[step] = st.tokens_by_step.get(step, 0) + spent
                if st.iterations:
                    st.current.tokens += spent
                self.save()
        except BudgetExceeded as exc:
            logger.error("%s", exc)
            self._stop("budget_exhausted", str(exc))
        except Exception as exc:
            logger.exception("run failed at step %s", st.next_step)
            self._stop("failed", f"step {st.next_step}: {exc}")
            raise
        logger.info("run %s finished: %s %s", self.state.run_id, self.state.status, self.state.message)
        return self.state

    def _stop(self, status: str, message: str) -> None:
        """Record the status in the last checkpoint (never in a half-finished step), which ``resume`` restarts."""
        state = RunState.model_validate_json((self.run_dir / STATE_FILE).read_text(encoding="utf-8"))
        state.status, state.message = status, message
        state.tokens_used, state.tokens_by_task = self.llm.tokens_used, dict(self.llm.tokens_by_task)
        self.state = self.ctx.state = state
        self.save()
        write_outputs(state, self.run_dir, self.cfg)
