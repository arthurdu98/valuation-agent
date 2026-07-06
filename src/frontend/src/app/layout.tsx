import type { Metadata } from "next";
import "./globals.css";
import { Providers } from "./providers";
import { Sidebar } from "@/components/layout/Sidebar";

export const metadata: Metadata = {
  title: "估值监控系统",
  description: "多行业估值监控与智能体辩证分析系统",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="zh-CN" className="h-full antialiased">
      <body className="min-h-full flex">
        <Providers>
          <Sidebar />
          <main className="flex-1 overflow-auto p-6">{children}</main>
        </Providers>
      </body>
    </html>
  );
}
