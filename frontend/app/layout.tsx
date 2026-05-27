import "./../styles/globals.css";

export const metadata = {
  title: "Invoice Processor",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="bg-white dark:bg-gray-900">{children}</body>
    </html>
  );
}

