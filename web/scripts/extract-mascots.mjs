#!/usr/bin/env node
/**
 * Mascot Sprite Extraction Script
 * 
 * This script uses sharp to extract individual mascot images from the sprite sheet.
 * Custom crop regions are used to avoid capturing adjacent mascot props.
 * 
 * Sprite layout (4x2 grid):
 * Row 0: [Analyst/Pie Chart] [Teacher/Blackboard] [Banker/Coins] [Laptop]
 * Row 1: [Presenter/Screen] [Money Handler] [Detective] [Wallet]
 */

import sharp from 'sharp';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const assetsDir = path.join(__dirname, '../src/assets/mascots');
const spriteSheet = path.join(assetsDir, 'finley-sprites.png');

// Mascot definitions with CUSTOM crop regions to avoid capturing adjacent props
// Values are percentages of the sprite sheet dimensions
const mascots = [
  // Row 0
  { 
    name: 'finley-analyst', 
    level: 3,
    // Pie chart mascot - leftmost, crop tightly to avoid teacher's blackboard
    region: { leftPct: 0.00, topPct: 0.00, widthPct: 0.22, heightPct: 0.50 }
  },
  { 
    name: 'finley-teacher', 
    level: 2,
    // Teacher - has blackboard, crop to include board but not analyst or banker
    region: { leftPct: 0.20, topPct: 0.00, widthPct: 0.28, heightPct: 0.50 }
  },
  { 
    name: 'finley-banker', 
    level: 7,
    // Banker with coins and hat - centered crop
    region: { leftPct: 0.48, topPct: 0.00, widthPct: 0.24, heightPct: 0.50 }
  },
  { 
    name: 'finley-laptop', 
    level: 4,
    // Laptop mascot - rightmost in row 0, has laptop extending
    region: { leftPct: 0.72, topPct: 0.00, widthPct: 0.28, heightPct: 0.50 }
  },
  
  // Row 1
  { 
    name: 'finley-presenter', 
    level: 5,
    // Presenter with screen - leftmost in row 1
    region: { leftPct: 0.00, topPct: 0.50, widthPct: 0.25, heightPct: 0.50 }
  },
  { 
    name: 'finley-money', 
    level: 6,
    // Money handler with tray - centered
    region: { leftPct: 0.24, topPct: 0.50, widthPct: 0.26, heightPct: 0.50 }
  },
  { 
    name: 'finley-detective', 
    level: 8,
    // Detective with coat - centered
    region: { leftPct: 0.50, topPct: 0.50, widthPct: 0.24, heightPct: 0.50 }
  },
  { 
    name: 'finley-wallet', 
    level: 10,
    // Wallet mascot - rightmost, final form
    region: { leftPct: 0.74, topPct: 0.50, widthPct: 0.26, heightPct: 0.50 }
  },
];

// Also create a "base" mascot from the analyst (simplest form)
const baseMascot = { 
  name: 'finley-base', 
  level: 1,
  region: { leftPct: 0.00, topPct: 0.00, widthPct: 0.22, heightPct: 0.50 }
};

async function extractMascots() {
  try {
    // Get image metadata
    const metadata = await sharp(spriteSheet).metadata();
    const { width, height } = metadata;
    
    console.log(`Sprite sheet: ${width}x${height}`);
    console.log('');
    
    // Extract each mascot with custom regions
    const allMascots = [...mascots, baseMascot];
    
    for (const mascot of allMascots) {
      const { region } = mascot;
      
      // Calculate pixel values from percentages
      const left = Math.round(region.leftPct * width);
      const top = Math.round(region.topPct * height);
      const extractWidth = Math.round(region.widthPct * width);
      const extractHeight = Math.round(region.heightPct * height);
      
      const outputPath = path.join(assetsDir, `${mascot.name}.png`);
      
      await sharp(spriteSheet)
        .extract({
          left,
          top,
          width: extractWidth,
          height: extractHeight,
        })
        // Resize to consistent dimensions for UI
        .resize(200, 200, {
          fit: 'contain',
          background: { r: 0, g: 0, b: 0, alpha: 0 }
        })
        .toFile(outputPath);
      
      console.log(`✓ Extracted ${mascot.name}.png (Level ${mascot.level})`);
      console.log(`  Region: left=${left}, top=${top}, ${extractWidth}x${extractHeight}`);
    }
    
    console.log('');
    console.log('All mascots extracted successfully!');
    console.log('');
    console.log('Next step: Run the base64 encoder to update mascot-data.ts');
    
  } catch (error) {
    console.error('Error extracting mascots:', error);
    process.exit(1);
  }
}

// Also create a script to generate base64 data
async function generateBase64Data() {
  console.log('');
  console.log('Generating base64 data for mascot-data.ts...');
  
  const mascotDataPath = path.join(__dirname, '../src/lib/mascot-data.ts');
  
  const allMascots = [...mascots, baseMascot];
  const base64Data = {};
  
  for (const mascot of allMascots) {
    const imagePath = path.join(assetsDir, `${mascot.name}.png`);
    const imageBuffer = fs.readFileSync(imagePath);
    const base64 = imageBuffer.toString('base64');
    
    // Extract variant name from filename (e.g., 'finley-analyst' -> 'analyst')
    const variantName = mascot.name.replace('finley-', '');
    base64Data[variantName] = `data:image/png;base64,${base64}`;
  }
  
  // Generate TypeScript file
  const tsContent = `/**
 * Mascot Image Data - Base64 Encoded
 * 
 * Auto-generated by extract-mascots.mjs
 * DO NOT EDIT MANUALLY
 * 
 * To regenerate: cd web && node scripts/extract-mascots.mjs
 */

export const MASCOT_IMAGE_DATA: Record<string, string> = ${JSON.stringify(base64Data, null, 2)};

export default MASCOT_IMAGE_DATA;
`;
  
  fs.writeFileSync(mascotDataPath, tsContent);
  console.log(`✓ Generated ${mascotDataPath}`);
}

// Run both extraction and base64 generation
async function main() {
  await extractMascots();
  await generateBase64Data();
}

main();