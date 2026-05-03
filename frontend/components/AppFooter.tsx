"use client";

export default function AppFooter() {
  return (
    <footer className="border-t border-gray-200 bg-white">
      <div className="mx-auto max-w-5xl px-4 py-4 text-xs text-gray-600">
        Privacy note: no database is used in this version. Extracted invoice data stays in the browser
        session.
      </div>
    </footer>
  );
}

