import type { Metadata } from "next";
import { DM_Sans, Sora } from "next/font/google";
import { Toaster } from "sonner";

import "./globals.css";
import Providers from "./providers";

const bodyFont = DM_Sans({
  subsets: ["latin"],
  variable: "--font-body",
  display: "swap",
});

const displayFont = Sora({
  subsets: ["latin"],
  variable: "--font-display",
  display: "swap",
});

export const metadata: Metadata = {
  title: "TalentPlus AI",
  description: "TalentPlus AI Candidate Screening Frontend",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className={`${bodyFont.variable} ${displayFont.variable} [font-family:var(--font-body)]`}>
        <Providers>
          <main className="relative z-10 min-h-screen">{children}</main>
          <Toaster richColors position="top-right" />
        </Providers>
      </body>
    </html>
  );
}
