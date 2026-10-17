# Runtime corrections before v0.2.0 publication

The initial preparation record (70 tests) is historical, not the final acceptance result.

- Exact official Blender 5.2.2 download and SHA-256 verification succeeded.
- Run 39029836479 failed official extension validation: files permission reason had 68 characters, exceeding the 64-character maximum. Shortened the reason; regression failed first then passed.
- Run 39029999015 passed official validation but failed real scene generation: TextCurve.align_y does not accept BASELINE in 5.2.2. Changed it to BOTTOM_BASELINE; added a fail-first regression.
- Latest local full pure-Python/static/distribution suite: 72 passed. This is not a claim that the subsequent Blender run passed.
- Both real Blender integration scripts now run independently once official validation passes, so a failure in one does not hide the other.
- Final runtime outcome must be read from the latest PR #1 Actions run and its actual JSON/.blend/SVG artifacts.
- Interactive Windows dialogs, mouse, undo and visual layout still require user acceptance.
