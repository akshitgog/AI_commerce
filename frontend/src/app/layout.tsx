import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import { ColdStartOverlay } from "@/components/cold-start-overlay";
import { CommerceProvider } from "@/lib/services/provider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "AI Commerce Gateway",
  description:
    "AI proposes. Human authorizes. Merchant accepts. Trusted backend executes and verifies.",
};

interface LayoutProps { children: React.ReactNode; }
export default function RootLayout({ children }: LayoutProps) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col">
        <CommerceProvider>
          {children}
          <ColdStartOverlay />
        </CommerceProvider>
      </body>
    </html>
  );
}
