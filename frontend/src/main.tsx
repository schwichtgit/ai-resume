import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";

// Test: Update title to verify JavaScript is executing
document.title = "AI Resume — Loading...";
console.log("JavaScript bundle loaded successfully");

createRoot(document.getElementById("root")!).render(<App />);
