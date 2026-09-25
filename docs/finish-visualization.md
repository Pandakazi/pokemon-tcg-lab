# Finish visualization — PM QA handoff

Status: READY FOR PM FINISH-VISUALIZATION QA. This pass is not merged or certified.

## Presentation

`FinishImage` is the shared exact-finish layer used by `CardImage` and the enlarged-art dialog. Variations, exact Collection gallery/list cards, and Card Detail reuse it. The text-only deck tray is unchanged. Functional Library/Deck Builder gallery representatives remain neutral; their exact-detail/variation views show the finish. Normal, unspecified, and unsupported finishes render the original image without an overlay.

Holo uses a restrained iridescent gradient and pointer-positioned soft reflection over an approximate illustration region. The boundary is feathered. Illustration Rare and Special Illustration Rare metadata enable a broader Holo region that fades over the lower rules text. Reverse Holo instead lights the surrounding card body, excluding the approximate illustration rectangle, with a different diagonal color pattern. Both have faint static light at rest, stronger light under the pointer, and a smooth return to neutral on leave. This pass adds no card tilt.

## Region limitation

The shared API image field and TCGdex provider supply one flat low/high WebP per printing. Read-only inspection of the raw Gumshoos and Darkrai source records found finish/variant metadata but no pixel masks or artwork coordinates. Finish variants of a printing use the same base image. The CSS regions are normalized approximations, not authentic foil maps: unusual layouts, historical borders, rule-box cards, and some full-art rarities will not precisely match physical foil boundaries. Rarity only adjusts the region of an already known Holo finish; it never determines finish identity. No image analysis, generated assets, or external service was added.

## Interaction, performance, accessibility

- Pointer handlers stay on the actual `img`. Decorative layers use `pointer-events:none`; frames and whitespace have no competitive handlers. Existing 500 ms activation and popup grace behavior are unchanged.
- Only the active image receives CSS-variable updates; no animation loop, per-frame React state, canvas, video, persistent GPU promotion, or effect network request. One ResizeObserver per foil image measures its actual bounds on load/resize and disconnects on unmount. Normal images have no observer or foil wrapper. Media-query objects are reused across pointer events.
- Reduced motion and no-hover/touch environments retain different static Holo/Reverse treatments and all existing textual finish labels, without pointer-driven light. No touch gesture was introduced.
- Compact Variations frames, ownership, quantity controls, totals, navigation, image fallback, and enlargement stay intact. No backend, identity, preferred printing, collection, deck persistence, validation, source data, or analytics changes.

## Verification

- Production typecheck/build passed; 65 frontend tests passed, including 10 new finish tests.
- Four new real-browser checks passed: real Gumshoos Normal/Reverse/Holo comparison, image-bound alignment, pointer coordinates/return to rest, frame whitespace, reduced motion, navigation/enlargement, unchanged deck response, 1440/1280/1100 layouts, multiple finish tiles with no idle animations, dark/bright artwork, and an emulated touch device.
- Eight existing browser checks passed across Collection and Phase 5 QA: gallery/list image-only 500 ms hover, cancellation/grace, ownership/preferences, mixed-printing controls/persistence, settled frames, centered controls, detail geometry, and fallback.
- Screenshots were inspected for Gumshoos at rest, active Holo/Reverse, enlarged Reverse, Darkrai, Umbreon, and the multi-card Boss family. This is a focused desktop Chromium/emulated-touch check, not a broad hardware GPU benchmark or real-device matrix.

## PM check

Open the QA runtime at `/deck-builder/cards/me01-110?variant=normal`, then **Variations**. Compare the three settled Gumshoos tiles, move across Holo and Reverse, then leave the image. Inspect finish intensity and readability at your usual display settings. Mike decides whether the visual treatment is acceptable for certification.
