const fs = require("fs");
const path = require("path");
const sharp = require("sharp");

const root = path.resolve(__dirname, "..");
const assets = path.join(root, "assets");
const brand = path.join(root, "custom_components", "power_outage_tracker", "brand");

const variants = [
  ["power-outage-tracker-icon-light.svg", "icon.png", "icon@2x.png"],
  ["power-outage-tracker-icon-dark.svg", "dark_icon.png", "dark_icon@2x.png"],
];

async function main() {
  fs.mkdirSync(brand, { recursive: true });

  for (const [sourceName, normalName, hdpiName] of variants) {
    const source = path.join(assets, sourceName);
    await sharp(source).resize(256, 256).png({ compressionLevel: 9 }).toFile(path.join(brand, normalName));
    await sharp(source).resize(512, 512).png({ compressionLevel: 9 }).toFile(path.join(brand, hdpiName));
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
