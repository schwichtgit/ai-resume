import { createRoot } from 'react-dom/client';
import { initOtel } from './lib/otel';
import App from './App.tsx';
import './index.css';

// Initialize OpenTelemetry tracing before React renders.
// No-op unless window.__OTEL_ENDPOINT__ is set by nginx/lua.
initOtel();

// Test: Update title to verify JavaScript is executing
document.title = 'AI Resume — Loading...';
console.log('JavaScript bundle loaded successfully');

createRoot(document.getElementById('root')!).render(<App />);
