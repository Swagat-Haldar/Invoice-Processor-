import "./../styles/globals.css";

export const metadata = {
  title: "Invoice Processor",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}

