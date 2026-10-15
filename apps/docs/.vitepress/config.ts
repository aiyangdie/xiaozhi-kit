import { defineConfig } from "vitepress";

export default defineConfig({
  title: "Xiaozhi Kit",
  description: "Open-source toolkit for ESP32 Xiaozhi — CLI, Web console, AI Skill",
  base: "/xiaozhi-kit/",
  themeConfig: {
    nav: [
      { text: "Guide", link: "/guide/install" },
      { text: "CLI", link: "/guide/cli" },
      { text: "GitHub", link: "https://github.com/xiaozhi-kit/xiaozhi-kit" },
    ],
    sidebar: [
      {
        text: "Guide",
        items: [
          { text: "Introduction", link: "/" },
          { text: "Install", link: "/guide/install" },
          { text: "CLI", link: "/guide/cli" },
          { text: "Web Console", link: "/guide/web" },
          { text: "Cursor Skill", link: "/guide/skill" },
          { text: "Troubleshooting", link: "/guide/troubleshoot" },
        ],
      },
      {
        text: "Project",
        items: [
          { text: "Roadmap", link: "/project/roadmap" },
          { text: "Contributing", link: "/project/contributing" },
        ],
      },
    ],
    socialLinks: [
      { icon: "github", link: "https://github.com/xiaozhi-kit/xiaozhi-kit" },
    ],
    footer: {
      message: "Released under the MIT License.",
      copyright: "Copyright © 2026 Xiaozhi Kit Contributors",
    },
  },
});
