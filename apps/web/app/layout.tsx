import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AddressAI México",
  description: "Interpretación probabilística de direcciones mexicanas dictadas."
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="es-MX">
      <body>{children}</body>
    </html>
  );
}
