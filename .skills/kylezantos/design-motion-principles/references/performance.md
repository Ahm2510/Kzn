# Motion Performance

Smooth animations must run at 60fps (or higher on ProMotion displays).

## 1. The "Golden Four"
Only animate properties that the browser can handle on the GPU without triggering a "Reflow" or "Repaint":
1. `transform` (translate, scale, rotate, skew)
2. `opacity`
3. `filter` (blur, brightness, etc. - use sparingly)
4. `clip-path`

## 2. Will-Change
Use the `will-change` property as a last resort for elements that are struggling to animate smoothly.
```css
.complex-element {
  will-change: transform, opacity;
}
```
**Warning**: Don't apply this to everything; it consumes significant memory.

## 3. Avoid Large Layout Shifts
When an element's size changes, it pushes other elements. This is expensive.
- **Solution**: Use `layoutId` (Framer Motion) or the FLIP technique to animate the *visual* transition while the actual layout "snaps" to the new position.

## 4. JS vs CSS
- Use **CSS** for simple, repetitive animations (hover, infinite loops).
- Use **JavaScript** (Framer Motion, GSAP) for complex, state-driven, or interruptible transitions.
