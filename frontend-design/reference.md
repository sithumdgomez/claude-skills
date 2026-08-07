# Motion & Layout Syntax Reference

Working syntax only for the newer techniques referenced in SKILL.md's Motion and Responsive Systems sections. This is not design guidance — it's here because these APIs are new enough that getting the shape right from memory is harder than getting the design decision right from principles.

## View Transitions API (page/state transitions)

Same-document transition — name matching elements across states and the browser morphs between them automatically:

```css
.thumbnail {
  view-transition-name: hero-image;
}
.hero-image {
  view-transition-name: hero-image; /* same name on the destination element */
}
```

```js
function navigateWithTransition(updateDOM) {
  if (!document.startViewTransition) {
    updateDOM(); // fallback: no transition, just apply the change
    return;
  }
  document.startViewTransition(() => updateDOM());
}
```

Fallback matters — call `updateDOM()` directly when `startViewTransition` isn't supported, don't skip the state change itself.

## CSS Scroll-Driven Animations (scroll-tied effects)

Animate progress as the user scrolls, no JS scroll listener:

```css
@keyframes reveal {
  from { opacity: 0; transform: translateY(24px); }
  to   { opacity: 1; transform: translateY(0); }
}

.section {
  animation: reveal linear both;
  animation-timeline: view();       /* ties progress to the element entering the viewport */
  animation-range: entry 0% cover 30%;
}
```

For a scrollbar-linked (not element-linked) timeline, use `animation-timeline: scroll()` instead of `view()`.

Fallback: wrap in `@supports (animation-timeline: view())` and provide a simple `IntersectionObserver`-triggered class-toggle for browsers that don't support it yet.

## CSS Container Queries (component-level responsiveness)

Adapt a component to its container's width, not the viewport's:

```css
.card-wrap {
  container-type: inline-size;
  container-name: card;
}

@container card (min-width: 400px) {
  .card {
    grid-template-columns: 120px 1fr;
  }
}
```

Every component that needs to be reused at different widths on the same page (a sidebar card vs. the same card full-width) is a candidate for this instead of a page-level media query.
