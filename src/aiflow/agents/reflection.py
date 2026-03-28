"""Generate-Critique-Improve reflection loop.

Implements the iterative pattern where a *generator* produces output, a
*critic* scores it, and if the score is below a threshold the generator is
asked to *improve*.  The loop repeats until the quality target is met or a
maximum iteration count is reached.
"""

from typing import Any, Awaitable, Callable

from pydantic import BaseModel, Field

import structlog

__all__ = ["ReflectionLoop", "ReflectionResult", "ReflectionIteration"]

logger = structlog.get_logger(__name__)


# ------------------------------------------------------------------
# Data models
# ------------------------------------------------------------------


class ReflectionIteration(BaseModel):
    """Record of a single generate/critique iteration.

    Attributes:
        iteration: 1-based iteration number.
        output: The generated (or improved) output for this iteration.
        score: Quality score assigned by the critic (0.0 - 1.0).
        feedback: Textual critique returned alongside the score.
    """

    iteration: int
    output: Any
    score: float
    feedback: str = ""


class ReflectionResult(BaseModel):
    """Final result of a reflection loop execution.

    Attributes:
        iterations: Total number of generate/critique cycles performed.
        final_output: The best output produced (last iteration's output).
        final_score: Quality score of *final_output*.
        improvement_history: Ordered list of per-iteration records.
    """

    iterations: int
    final_output: Any
    final_score: float
    improvement_history: list[ReflectionIteration] = Field(default_factory=list)


# ------------------------------------------------------------------
# Type aliases for the callback functions
# ------------------------------------------------------------------

GeneratorFn = Callable[..., Awaitable[Any]]
"""Async callable: (input, **context) -> output"""

CriticFn = Callable[..., Awaitable[tuple[float, str]]]
"""Async callable: (output, **context) -> (score, feedback)"""


# ------------------------------------------------------------------
# Reflection loop
# ------------------------------------------------------------------


class ReflectionLoop:
    """Orchestrates the generate -> critique -> improve cycle.

    Args:
        generator: Async function that produces an initial output (and later
            an improved output given previous feedback).  Signature:
            ``async (input_data, feedback=None, previous_output=None) -> output``
        critic: Async function that evaluates an output and returns a tuple
            of ``(score, textual_feedback)``.  Signature:
            ``async (output) -> (float, str)``
        max_iterations: Hard upper bound on generate/critique cycles.
        quality_threshold: Minimum critic score in ``[0.0, 1.0]`` required to
            accept the output and exit early.
    """

    def __init__(
        self,
        generator: GeneratorFn,
        critic: CriticFn,
        max_iterations: int = 3,
        quality_threshold: float = 0.8,
    ) -> None:
        self._generator = generator
        self._critic = critic
        self._max_iterations = max_iterations
        self._quality_threshold = quality_threshold

    # ------------------------------------------------------------------
    # Main loop
    # ------------------------------------------------------------------

    async def run(self, input_data: Any) -> ReflectionResult:
        """Execute the reflection loop.

        1. **Generate** -- call the generator with the original input.
        2. **Critique** -- call the critic to score the output.
        3. **Check** -- if the score meets the threshold, return.
        4. **Improve** -- call the generator again, passing the previous
           output and the critic's feedback, then go to step 2.

        Args:
            input_data: The seed input for the generator on the first call.

        Returns:
            A :class:`ReflectionResult` containing the best output, its
            score, and the full improvement history.
        """
        history: list[ReflectionIteration] = []
        current_output: Any = None
        current_score: float = 0.0
        feedback: str = ""

        for i in range(1, self._max_iterations + 1):
            log = logger.bind(iteration=i, max_iterations=self._max_iterations)

            # --- Generate / Improve ---
            if i == 1:
                current_output = await self._generator(input_data)
            else:
                current_output = await self._generator(
                    input_data,
                    feedback=feedback,
                    previous_output=current_output,
                )

            # --- Critique ---
            current_score, feedback = await self._critic(current_output)

            iteration_record = ReflectionIteration(
                iteration=i,
                output=current_output,
                score=current_score,
                feedback=feedback,
            )
            history.append(iteration_record)

            log.info(
                "reflection_iteration",
                score=round(current_score, 4),
                threshold=self._quality_threshold,
                passed=current_score >= self._quality_threshold,
            )

            # --- Early exit if quality is met ---
            if current_score >= self._quality_threshold:
                logger.info(
                    "reflection_converged",
                    iterations=i,
                    final_score=round(current_score, 4),
                )
                break

        result = ReflectionResult(
            iterations=len(history),
            final_output=current_output,
            final_score=current_score,
            improvement_history=history,
        )

        if current_score < self._quality_threshold:
            logger.warning(
                "reflection_max_iterations_reached",
                iterations=len(history),
                final_score=round(current_score, 4),
                threshold=self._quality_threshold,
            )

        return result
