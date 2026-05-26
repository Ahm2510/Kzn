# Audit Output Format

When providing an audit, follow this structure:

---

## 🔎 Motion Audit: [Feature Name]

### 🏗️ Technical Foundation
*Analysis of the current implementation (easing, performance, properties).*
- **Observation**: [e.g., Using `left` for animation instead of `translate`]
- **Risk**: [e.g., Causes layout jank on low-end devices]

### 🎨 Designer Perspectives

#### Emil Kowalski (Tactile & Professional)
> "[Critique based on Emil's principles]"
- **Suggestion**: Add a `scale(0.97)` on `:active` and use a `bounce: 0` spring.

#### Jakub Krehel (Visual & Refined)
> "[Critique based on Jakub's principles]"
- **Suggestion**: Add a subtle `blur` to the enter animation and check the optical alignment of the [icon].

#### Jhey Tompkins (Creative & Modern)
> "[Critique based on Jhey's principles]"
- **Suggestion**: Use CSS `linear()` for the bounce effect or try a 3D Z-axis transition.

### 🛠️ Proposed Implementation
```jsx
// [Refined code snippet here]
```
---
