"use client";

import ThemeToggle from "./ThemeToggle";

export default function AppHeader() {
  return (
    <header className="border-b border-gray-200 bg-white dark:border-gray-700 dark:bg-gray-900">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
        <div>
          <h1 className="text-xl font-semibold text-gray-900 dark:text-gray-100">Invoice Processor</h1>
          <p className="mt-1 text-sm text-gray-600 dark:text-gray-400">Gemini Vision-Language extraction into structured JSON</p>
        </div>
        <ThemeToggle />
      </div>
    </header>
  );
}

