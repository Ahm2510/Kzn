# Jhey Tompkins Perspective
*Focus: Creative CSS, 3D CSS, and scroll-driven interactions.*

### 1. "Think in Cuboids"
Jhey approaches UI like a 3D space. Even flat elements can have Z-axis depth.
- Use `transform-style: preserve-3d` and `perspective` to create real depth.
- Animate elements on the Z-axis for unique "stacking" transitions.

### 2. Scroll-Driven Animation (SDA)
Use the latest CSS `animation-timeline: scroll()` and `view()` features.
- **The Pattern**: Tie animation progress to scroll position without using heavy JavaScript scroll listeners.
- **Trigger Pattern**: Use SDA to "arm" an animation that then plays with a fixed duration (severing the tie between scroll speed and animation speed).

### 3. The `linear()` Function
Use the new CSS `linear()` function for complex easing curves (bounce, elastic) that were previously only possible in JavaScript.

### 4. Negative Delays for Staggering
To create a "continuous" staggered effect (like a loading wave), use negative `animation-delay` based on an element's index.
```css
.item { animation-delay: calc(var(--index) * -0.2s); }
```
