# Emil Kowalski Perspective
*Focus: High-end craft, tactile feedback, and professional UI springs.*

### 1. Tactile Feedback
Emil emphasizes that the web should feel physical. Every interaction should have a "reaction."
- **Scale on Press**: Buttons should scale down slightly (`0.97`) when clicked.
- **Immediate Response**: Don't wait for an API call to show *something* happened.

### 2. Professional Springs
Avoid "bouncy" animations in professional tools. Use "high-damping" springs.
- **The Config**: `stiffness: 300, damping: 30` or `bounce: 0`.
- **Interruptibility**: If a user clicks away before an animation is done, the UI should immediately start the next transition from its current state, not finish the first one.

### 3. Masking with Blur
When state transitions aren't perfectly smooth (e.g., changing a complex layout), use a subtle blur (`2px`) during the transition to mask the "jump."

### 4. Momentum-Based Dismissal
When dragging to dismiss (like a mobile sheet), the threshold should be based on **velocity**, not just distance. A fast, short flick should dismiss as easily as a slow, long drag.
