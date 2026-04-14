# 📚 Kindleizer - Espresso Edition ☕️

<p align="center">
  <img src="app_icon.png" alt="Kindleizer App Icon" width="200" style="border-radius: 40px; box-shadow: 0 10px 20px rgba(0,0,0,0.2);" />
</p>

## 📖 What is Kindleizer?
Reading PDFs on a Kindle is often a nightmare—tiny fonts, huge margins, and the constant need to zoom in and out. **Kindleizer** is a lightweight macOS utility that solves this by transforming static PDFs into perfectly formatted, Kindle-friendly documents. 

It takes your complex PDFs and re-flows them specifically for e-ink screens, ensuring your text is large, clear, and perfectly cropped.

## 🚀 Why Use Kindleizer?
* **Readability First:** Automatically crops white margins and optimizes font sizes so you can actually read research papers and books without straining your eyes.
* **No More Bloat:** Forget heavy alternatives like Calibre for simple conversions. Kindleizer is a "drop and convert" tool designed for speed.
* **Smart Reflow:** Powered by the **K2pdfopt engine**, it intelligently handles multi-column layouts and complex PDF structures that standard converters fail to process.
* **Crafted for Mac:** A warm, native 'Espresso Edition' interface that makes the experience effortless!

## ✨ Features
* **One-Click Optimization:** Powered by the incredible **K2pdfopt engine** under the hood, turning complex terminal commands into a single, elegant button.
* **Smart Device Profiles:** Fully supports all resolutions, from legacy Paperwhites to the new Colorsoft and 10.2" Scribe.
* **Native Mac Experience:** Forget standard gray windows. Kindleizer features a beautiful, distraction-free matte dark reader interface.
* **Drag & Drop:** Simply drop your PDF into the app and let it do the heavy lifting.

## 📥 Installation & Download

👉[Download Kindleizer v1.0 DMG](https://github.com/hundebach/kindleizer/releases/latest)

1. Download the `.dmg` file from the link above and double-click to open it.
2. Drag the **Kindleizer** icon into your **Applications** folder.

**⚠️ Important macOS Security Note:**
Since this is an indie app not signed with an expensive Apple Developer certificate, macOS will show a security warning (Gatekeeper) on the first launch. Don't worry, it's safe! 
To bypass this:
* Go to your **Applications** folder.
* **Right-click (or Control-click)** on Kindleizer and select **"Open"**.
* Click **"Open"** again in the prompt. macOS will now remember it as safe, and you can open it normally next time!

### 2. If it says "App is Damaged" or "Cannot be Opened" (The Quarantine Fix)
If you already tried to open it and macOS moved it to "quarantine" or says it's damaged, follow these steps to reset it:
1. Open your **Terminal** (Cmd + Space, type 'Terminal').
2. Copy and paste the following command:
   ```bash
   xattr -cr /Applications/Kindleizer.app
3. Press Enter. Now try opening the app normally—it will work perfectly!

## 🤝 Support (Buy Me a Coffee)

I developed this tool completely for free to speed up my own PDF reading workflow. If it makes your life easier and you enjoy the "Espresso Edition" vibe, consider buying me my next coffee and thank you so much for your support!

[<img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" width="200" alt="Buy Me A Coffee">](INSERT_YOUR_BUY_ME_A_COFFEE_OR_GUMROAD_LINK_HERE)

---
*Developed with passion by a gastronomy and tech enthusiast in Padua, Italy. 🇮🇹*

## 📜 Credits & Acknowledgments

Kindleizer is a graphical wrapper built with Python. The heavy lifting of PDF optimization is performed by the legendary **K2pdfopt engine**.

* **Core Engine:** Huge thanks to **Willus** for creating [K2pdfopt](https://www.willus.com/k2pdfopt/), the most powerful open-source PDF optimizer.
* **Design & Wrapper:** Developed by [Hundebach](https://github.com/hundebach) to provide a seamless macOS experience.
