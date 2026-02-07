import React from "react"
import type { Metadata, Viewport } from "next"
import { DM_Sans, JetBrains_Mono } from "next/font/google"

import "./globals.css"

const _dmSans = DM_Sans({ subsets: ["latin"], variable: "--font-dm-sans" })
const _jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
})

export const metadata: Metadata = {
  title: "Ops Assistant",
  description: "AI-powered assistant for querying indoor location-tracking data in retail store operations",
}

export const viewport: Viewport = {
  themeColor: "#0d9668",
}

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode
}>) {
  return (
    <html lang="en" className="dark">
      <body className={`${_dmSans.variable} ${_jetbrainsMono.variable} font-sans antialiased overflow-hidden`}>{children}</body>
    </html>
  )
}
