# Motion Accessibility (A11y)

Motion is a powerful tool, but it can cause physical distress (nausea, dizziness, seizures) for users with vestibular disorders.

## 1. Respect Reduced Motion
Always respect the `prefers-reduced-motion` media query.

### CSS Strategy
```css
@media (prefers-reduced-motion: reduce) {
  *, ::before, ::after {
    animation-delay: -1ms !important;
    animation-duration: 1ms !important;
    animation-iteration-count: 1 !important;
    background-attachment: initial !important;
    scroll-behavior: auto !important;
    transition-duration: 0s !important;
    transition-delay: 0s !important;
  }
}
```

### Framer Motion Strategy
Use the `useReducedMotion` hook to conditionally disable or simplify animations:
```jsx
const shouldReduceMotion = useReducedMotion();
const variants = {
  initial: { opacity: 0, x: shouldReduceMotion ? 0 : -20 },
  animate: { opacity: 1, x: 0 }
};
```

## 2. Avoid Large-Scale Movement
Movements that cover a large portion of the screen (parallax, full-page slides) are the most likely to cause vestibular issues.

**Mitigation**: Replace large translations with subtle opacity fades for users who prefer reduced motion.

## 3. Don't Rely Solely on Motion
Motion should reinforce a state change, not be the *only* way that change is communicated.
- Ensure text labels or icons update clearly even if the animation doesn't play.
- Provide clear visual indicators for interactive states (focus, active) that don't depend on movement.

## 4. Allow Users to Disable Motion
For sites with heavy experimental motion (Jhey-style creative experiments), consider providing a global toggle in the UI settings.
