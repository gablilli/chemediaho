# TypeScript Setup

This project now uses TypeScript for all JavaScript code, including the service worker and page scripts.

## Directory Structure

```
├── src/                      # TypeScript source files
│   ├── sw.ts                 # Service Worker
│   ├── common.ts             # Shared utilities (theme, logout, etc.)
│   ├── login.ts              # Login page logic
│   ├── charts.ts             # Charts page logic
│   ├── goal.ts               # Goal calculator logic
│   ├── grades.ts             # Grades page logic
│   ├── export.ts             # Export page logic
│   └── info.ts               # Info page logic
├── static/
│   ├── sw.js                 # Compiled service worker
│   └── js/                   # Compiled page scripts
│       ├── common.js
│       ├── login.js
│       ├── charts.js
│       ├── goal.js
│       ├── grades.js
│       ├── export.js
│       └── info.js
├── tsconfig.json             # TypeScript config for page scripts
├── tsconfig.sw.json          # TypeScript config for service worker
└── package.json              # npm dependencies and build scripts
```

## Building

To compile the TypeScript files:

```bash
npm run build
```

This will:
1. Compile page scripts from `src/*.ts` to `static/js/*.js`
2. Compile service worker from `src/sw.ts` to `static/sw.js`

Individual builds:
```bash
npm run build:pages    # Build page scripts only
npm run build:sw       # Build service worker only
npm run watch          # Watch for changes and rebuild
npm run clean          # Remove compiled files
```

## Development

1. Make changes to TypeScript files in the `src/` directory
2. Run `npm run build` to compile
3. Refresh the browser to see changes

For continuous development, use:
```bash
npm run watch
```

## Integration with Flask Templates

The HTML templates inject backend data into `window` object for TypeScript modules:

```html
<!-- Example from charts.html -->
<script>
  window.gradesData = {{ grades_avr | tojson | safe }};
</script>
<script type="module" src="/static/js/charts.js"></script>
```

## Key Features

- **Type Safety**: TypeScript provides compile-time type checking
- **ES Modules**: Modern JavaScript module system
- **Source Maps**: Included for debugging compiled code
- **Shared Code**: Common utilities in `common.ts` reduce duplication
- **Service Worker Types**: Proper typing for Service Worker API

## Notes

- Compiled JavaScript files are ES2020 modules
- Source maps (`.js.map`) help with debugging
- The `static/js/` directory is generated and should not be edited directly
- Always edit TypeScript files in `src/` directory
