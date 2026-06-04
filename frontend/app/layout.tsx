import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "India Influencer Finder",
  description: "Discover, enrich, classify, and refresh Indian Instagram creators.",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
