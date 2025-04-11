# Staples Brain Frontend

This directory contains the frontend React application for Staples Brain.

## Structure

- `src/` - Source code for the React application
- `public/` - Static files for the React application
- `build/` - Production build (generated)

## Development

To start the development server:

```bash
cd frontend
npm install
npm start
```

The frontend will be available at http://localhost:3000 and will proxy API requests to the backend.

## Building for Production

To build the frontend for production:

```bash
cd frontend
npm run build
```

The production build will be available in the `build/` directory.

## Technology Stack

- React 18.x
- React Router 6.x
- Bootstrap 5.x
- Axios for API requests
- Chart.js for data visualization