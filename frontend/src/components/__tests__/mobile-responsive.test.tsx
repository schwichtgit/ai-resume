import { describe, it, expect } from "vitest";
import fs from "fs";
import path from "path";

describe("Mobile Responsive", () => {
  it("responsive breakpoint classes exist in Hero component", () => {
    const heroPath = path.resolve(__dirname, "../Hero.tsx");
    const content = fs.readFileSync(heroPath, "utf-8");

    // Verify responsive classes are used
    expect(content).toContain("sm:");
    expect(content).toContain("md:");
  });

  it("responsive breakpoint classes exist in AIChat component", () => {
    const chatPath = path.resolve(__dirname, "../AIChat.tsx");
    const content = fs.readFileSync(chatPath, "utf-8");

    // AIChat uses sm: breakpoints and touch-friendly min-height targets
    expect(content).toContain("sm:");
    expect(content).toContain("min-h-[44px]");
  });

  it("responsive breakpoint classes exist in FitAssessment component", () => {
    const fitPath = path.resolve(__dirname, "../FitAssessment.tsx");
    const content = fs.readFileSync(fitPath, "utf-8");

    expect(content).toContain("sm:");
  });

  it("touch target sizes meet accessibility minimum in AIChat", () => {
    const chatPath = path.resolve(__dirname, "../AIChat.tsx");
    const content = fs.readFileSync(chatPath, "utf-8");

    // 44px minimum touch target (WCAG 2.5.5)
    expect(content).toContain("min-w-[44px]");
    expect(content).toContain("min-h-[44px]");
  });

  it("Hero uses mobile-first responsive text sizes", () => {
    const heroPath = path.resolve(__dirname, "../Hero.tsx");
    const content = fs.readFileSync(heroPath, "utf-8");

    // Should have progressive text sizing: base -> sm -> md -> lg
    expect(content).toContain("sm:text-");
    expect(content).toContain("md:text-");
  });
});
