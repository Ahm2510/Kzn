# Motion Audit Checklist

Use this checklist when performing a `design-motion-principles audit`.

## 1. Interaction & Feedback
- [ ] **Tactile Response**: Do buttons/links have a `:active` scale or color shift?
- [ ] **Intent Signal**: Does the UI react *before* the action (hover/focus) and *during* the action?
- [ ] **State Confidence**: Is it clear when an action (copy, delete, save) has succeeded?

## 2. Easing & Timing
- [ ] **No Linear Easing**: Are there any default `linear` or `ease` curves that feel robotic?
- [ ] **Refined Springs**: Are entering elements using professional springs (e.g., `bounce: 0`)?
- [ ] **Duration vs. Distance**: Do larger movements take slightly longer, or is everything at a fixed 300ms?

## 3. Continuity & Flow
- [ ] **Origin Awareness**: Do dropdowns/modals originate from the point of trigger?
- [ ] **Shared Layouts**: Can `layoutId` (FLIP) be used to transition between states rather than hard swaps?
- [ ] **Progressive Disclosure**: Does the UI guide the eye to new content as it appears?

## 4. Visual Quality
- [ ] **Materializing Effects**: Are enter animations using the Jakub Recipe (opacity + translate + blur)?
- [ ] **Subtle Exits**: Are exit animations softer and less distracting than enter animations?
- [ ] **Shadows vs Borders**: In light mode, could multi-layer shadows replace flat borders for better depth?

## 5. Performance & A11y
- [ ] **GPU Acceleration**: Are animations limited to `transform`, `opacity`, `filter`, and `clip-path`?
- [ ] **Reduced Motion**: Is `prefers-reduced-motion` handled?
- [ ] **Interruptibility**: If I click/hover rapidly, does the UI jump or does it blend smoothly?
