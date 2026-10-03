/**
 * FairFold — Tailwind configuration.
 *
 * Specified in design.md §11.2. Every colour here is a CSS custom property
 * defined in `static/css/tokens.css`, which is compiled from design.md §3–§5.
 * Nothing in this file may contain a literal colour value: the tokens are the
 * single source of truth, and a hex code added here creates a second one that
 * no one remembers to update.
 *
 * Every utility name maps to a *semantic* role (`ink`, `surface`, `danger`),
 * never to a hue (`grey-500`, `red-600`). A page that says `text-danger` still
 * reads correctly when the palette changes; one that says `text-red-600` encodes
 * a decision that belongs to design.md and not to a template.
 */

/** @type {import('tailwindcss').Config} */
module.exports = {
  // Both globs are needed. The first covers templates/ at the repository root;
  // the second covers each app's own templates/ directory. Dropping the second
  // does not error -- it silently produces a stylesheet missing every class used
  // in app templates, which is why CI asserts the 30 KB size budget.
  content: ["./templates/**/*.html", "./**/templates/**/*.html"],

  // Preflight is on deliberately: the reset is what makes the type and spacing
  // scale in design.md §4 actually apply. It is listed here only to note that it
  // is NOT being trimmed — a `corePlugins: {}` reset would silently drop the
  // `dialog` element styling that the Override Reason Dialog (design.md §7.11)
  // depends on, and that dialog must work without a JS polyfill.
  corePlugins: {
    lineClamp: true,
  },

  theme: {
    extend: {
      colors: {
        bg: "var(--bg)",
        surface: {
          DEFAULT: "var(--surface)",
          muted: "var(--surface-muted)",
        },
        ink: {
          DEFAULT: "var(--ink)",
          2: "var(--ink-2)",
          3: "var(--ink-3)",
          4: "var(--ink-4)",
        },
        primary: {
          DEFAULT: "var(--primary)",
          strong: "var(--primary-strong)",
          soft: "var(--primary-soft)",
        },
        success: {
          DEFAULT: "var(--success)",
          soft: "var(--success-soft)",
          ink: "var(--success-ink)",
        },
        warning: {
          DEFAULT: "var(--warning)",
          soft: "var(--warning-soft)",
          ink: "var(--warning-ink)",
        },
        danger: {
          DEFAULT: "var(--danger)",
          soft: "var(--danger-soft)",
          ink: "var(--danger-ink)",
        },
        info: {
          DEFAULT: "var(--info)",
          soft: "var(--info-soft)",
          ink: "var(--info-ink)",
        },
        // The AI palette is separate from the status palette on purpose. An AI
        // output is not a success or a warning, and colour-coding it as either
        // would suggest the system judged it. design.md §11.5.
        ai: {
          DEFAULT: "var(--ai)",
          soft: "var(--ai-soft)",
          ink: "var(--ai-ink)",
        },
        border: {
          DEFAULT: "var(--border)",
          input: "var(--border-input)",
        },
      },

      borderRadius: {
        sm: "6px", // inputs, badges
        md: "10px", // buttons, cards
        lg: "16px", // modals
      },

      boxShadow: {
        card: "0 1px 2px rgba(15,23,42,.06), 0 1px 3px rgba(15,23,42,.10)",
        modal: "0 10px 30px rgba(15,23,42,.20)",
      },

      fontFamily: {
        // Fonts are self-hosted from /static/fonts/ (design.md §4.1); the CSP
        // allows no third-party font host.
        sans: [
          "Inter",
          "system-ui",
          "-apple-system",
          "Segoe UI",
          "Roboto",
          "sans-serif",
        ],
        // Bengali is Phase 5 (design.md, open decision 4). Declaring the family
        // now costs nothing and means no template changes when it ships.
        bn: ["Noto Sans Bengali", "Kalpurush", "sans-serif"],
        mono: ["ui-monospace", "SF Mono", "Menlo", "monospace"],
      },

      // design.md §4.2. Names are semantic, not sized, so rescaling the ramp does
      // not rename a class in every template. Each pairs size with its line
      // height because §4.2 specifies them together.
      fontSize: {
        display: ["2.25rem", { lineHeight: "2.75rem" }], // 36/44, hero only
        h1: ["1.875rem", { lineHeight: "2.375rem" }], // 30/38
        h2: ["1.5rem", { lineHeight: "2rem" }], // 24/32
        h3: ["1.25rem", { lineHeight: "1.75rem" }], // 20/28
        h4: ["1rem", { lineHeight: "1.5rem" }], // 16/24
        body: ["1rem", { lineHeight: "1.5rem" }], // 16/24
        "body-sm": ["0.875rem", { lineHeight: "1.25rem" }], // 14/20
        // 12px is the caption step and §4.2 restricts it to badges and
        // timestamps — "never for essential info". The bias-pass badge is the one
        // place that rule is stretched, which is why it also carries a word and a
        // tooltip rather than relying on the label alone.
        caption: ["0.75rem", { lineHeight: "1rem" }], // 12/16
        score: ["3rem", { lineHeight: "3.25rem" }], // 48/52
      },

      // design.md §8 caps motion at 150ms. Anything longer reads as lag on the
      // low-end devices and mid-range connections this product targets.
      transitionDuration: {
        DEFAULT: "150ms",
      },

      // design.md §5.3, verbatim. These match Tailwind's defaults, which is the
      // point: the layout was designed against them rather than fought.
      //
      // The mobile-first base is 0 with a single column, and every page is
      // designed at 360px first — see §5.3.
      screens: {
        sm: "640px", // two-column forms
        md: "768px", // sidebar becomes a collapsible rail
        lg: "1024px", // fixed sidebar 240px, content max 1152px
        xl: "1280px", // wide tables, split views
      },

      maxWidth: {
        // §5.3: content max 1152px at lg and above. A wider measure puts the
        // match-score column too far from the row label to compare them.
        content: "72rem", // 1152px
        prose: "60ch", // §4.2: 60–75 characters per line for prose
      },

      // §5.3: touch targets at least 44 × 44px on mobile.
      spacing: {
        touch: "2.75rem", // 44px
      },
    },
  },

  plugins: [],
};