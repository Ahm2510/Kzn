# Technical Principles

## 1. Enter & Exit Animations

### Enter Animation Recipe (Jakub)
A standard enter animation combines three properties:
- **Opacity**: 0 → 1
- **TranslateY**: ~8px → 0
- **Blur**: 4px → 0px

### Exit Animation Subtlety (Jakub)
**Key Insight**: Exit animations should be subtler than enter animations.
- Use a faster duration and less movement (e.g., `-12px` instead of the entering `20px`).

## 2. Easing & Timing

### Duration Impacts Naturalness
- Fast start, gentle stop (`ease-out`) for entering.
- Gentle start, fast exit (`ease-in`) for leaving.

### Custom Easing is Essential (Emil)
Avoid default CSS easing. Use custom Bézier curves or professional springs.
- **Spring**: `duration: 0.45, bounce: 0` (The "Emil Standard").

## 3. Visual Effects

### Shadows Instead of Borders (Jakub)
In light mode, prefer subtle multi-layer box-shadows over solid borders for better depth.

### OKLCH Gradients
Use `oklch` for gradients to avoid the "gray/muddy zone" in the middle of a transition.

## 4. Optical Alignment
If it looks wrong mathematically, trust your eyes. Shift icons and shapes until they *feel* centered.

## 5. Icon & State Animations
Animate icon swaps (copy → check) with a quick scale + opacity + blur transition to draw attention to the state change.

## 6. Shared Layout Animations (FLIP)
Use `layoutId` to morph elements from one state to another (e.g., a card expanding into a modal) instead of just fading them in and out.
