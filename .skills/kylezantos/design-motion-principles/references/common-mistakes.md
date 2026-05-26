# Common Motion Mistakes

## 1. The "Default Ease" Trap
Using the browser default `ease` or `ease-in-out` curves.
- **Effect**: Animations feel "default" and unpolished.
- **Fix**: Use custom Bézier curves (e.g., `cubic-bezier(0.16, 1, 0.3, 1)`) or spring physics.

## 2. Animating "Heavy" Properties
Animating `width`, `height`, `top`, `left`, or `margin`.
- **Effect**: Triggers layout recalculation on every frame, causing jank (stuttering).
- **Fix**: Use `transform` (scale, translate) and `clip-path` instead.

## 3. Scale(0) Starts
Starting scale animations from 0.
- **Effect**: Elements appear to pop out of nowhere, feeling "cartoonish" and unnatural.
- **Fix**: Start from `scale(0.9)` or `scale(0.95)` with opacity 0 for a more refined "materializing" feel.

## 4. Symmetrical Exits
Making the exit animation an exact mirror of the enter animation.
- **Effect**: The UI feels slow because users have to wait for things to leave with the same "importance" as they entered.
- **Fix**: Make exits faster, shorter, and subtler.

## 5. Over-Animating
Adding motion to every single element that changes.
- **Effect**: Visual noise; the user doesn't know where to look.
- **Fix**: Use motion only to guide attention or provide feedback on interaction.
