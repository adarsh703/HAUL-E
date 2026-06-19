import type { Metadata } from "next";
import "./globals.css";
import Sidebar from "@/components/Sidebar";
import TopHeader from "@/components/TopHeader";

export const metadata: Metadata = {
  title: "Haul-E TMS",
  description: "AI-Powered Transportation Management System",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>
        <div className="app-container">
          <Sidebar />
          <main className="main-content">
            <TopHeader />
            {children}
          </main>
        </div>
      </body>
    </html>
  );
}
