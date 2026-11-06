import type { Metadata, Viewport } from "next";
import "./globals.css";
import { Be_Vietnam_Pro, Space_Grotesk } from "next/font/google";
import { cn } from "@/lib/utils";
import { TooltipProvider } from "@/components/ui/tooltip";

const bodyFont = Be_Vietnam_Pro({
  subsets: ["latin", "vietnamese"],
  weight: ["400", "500", "600", "700"],
  variable: "--font-sans",
});

const displayFont = Space_Grotesk({
  subsets: ["latin", "vietnamese"],
  variable: "--font-display",
});

export const metadata: Metadata = {
  title: "RAG ChatBot - Chăm Sóc Khách Hàng Thông Minh",
  description:
    "Hệ thống chatbot AI tích hợp RAG (Retrieval-Augmented Generation) cho chăm sóc khách hàng hiệu quả, chính xác và tức thì.",
};

export const viewport: Viewport = {
  themeColor: "#f8fafc",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html
      lang="vi"
      suppressHydrationWarning
      className={cn(
        "font-sans",
        bodyFont.variable,
        displayFont.variable,
      )}
      data-scroll-behavior="smooth"
    >
      <body suppressHydrationWarning>
        <TooltipProvider>{children}</TooltipProvider>
      </body>
    </html>
  );
}
