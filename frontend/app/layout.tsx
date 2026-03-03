import type { Metadata } from "next";
import { Architects_Daughter, JetBrains_Mono, Crimson_Pro } from "next/font/google";
import "./globals.css";

const architectsDaughter = Architects_Daughter({
  weight: "400",
  variable: "--font-architects-daughter",
  subsets: ["latin"],
});

const jetbrainsMono = JetBrains_Mono({
  weight: ["400", "500", "700"],
  variable: "--font-jetbrains-mono",
  subsets: ["latin"],
});

const crimsonPro = Crimson_Pro({
  weight: ["400", "500", "600", "700"],
  variable: "--font-crimson-pro",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "LegacyLens — LAPACK Explorer",
  description: "RAG-powered search for the LAPACK Fortran codebase",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${architectsDaughter.variable} ${jetbrainsMono.variable} ${crimsonPro.variable}`}
      >
        {children}
      </body>
    </html>
  );
}
