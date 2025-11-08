/**
 * Bangla Date Image Generator and Bluesky Poster
 * Generates a dark-themed image with Bangla date information and posts to Bluesky
 */

import { AtpAgent, RichText } from '@atproto/api';
import { getDate, getDay, getMonth, getWeekDay, getYear } from 'bangla-calendar';
import { createCanvas, registerFont, loadImage } from 'canvas';
import dotenv from 'dotenv';
import fs from 'fs';
import https from 'https';
import path from 'path';
import { fileURLToPath } from 'url';
import sharp from 'sharp';
import { getBanglaOrdinal, getBanglaSeason } from './utils.js';

// ES module equivalent of __dirname
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

// Load environment variables (for local development)
dotenv.config({ path: path.join(__dirname, '../../.env') });

// Image dimensions - 1080x1080 square
const WIDTH = 1080;
const HEIGHT = 1080;

// Dark theme colors (similar to reference code)
const COLORS = {
  bg: '#0f172a',        // slate-950
  cardBg: '#1e293b',    // slate-900
  border: '#334155',    // slate-800
  textPrimary: '#e7e9ea',   // light text
  textSecondary: '#71767b', // gray text
  accent: '#0085ff'     // blue accent
};

// Font sizes (matching Python PIL font sizes)
const FONT_SIZES = {
  title: 72,
  date: 110,
  info: 68,
  small: 60
};

/**
 * Load fonts with fallback mechanism
 * Tries Ekush font first, then falls back to Hind Siliguri or system fonts
 */
function loadFonts() {
  const fontsDir = path.join(__dirname, '../../fonts');
  const ekushPath = path.join(fontsDir, 'Ekush-Regular.ttf');
  
  let fontFamily = 'sans-serif';
  let fontLoaded = false;
  
  // Try to load Ekush font (primary)
  if (fs.existsSync(ekushPath)) {
    try {
      registerFont(ekushPath, { family: 'Ekush' });
      fontFamily = 'Ekush';
      fontLoaded = true;
      console.log('✅ Loaded Ekush font');
    } catch (error) {
      console.warn('⚠️  Could not load Ekush font:', error.message);
    }
  }
  
  // Try fallback fonts if Ekush not loaded
  if (!fontLoaded) {
    const fallbackFonts = [
      { name: 'Hind Siliguri', patterns: ['Hind-Siliguri.ttf', 'HindSiliguri-Regular.ttf'] },
      { name: 'Noto Sans Bengali', patterns: ['NotoSansBengali-Regular.ttf'] }
    ];
    
    for (const fallback of fallbackFonts) {
      for (const pattern of fallback.patterns) {
        const fallbackPath = path.join(fontsDir, pattern);
        if (fs.existsSync(fallbackPath)) {
          try {
            registerFont(fallbackPath, { family: fallback.name });
            fontFamily = fallback.name;
            fontLoaded = true;
            console.log(`✅ Loaded fallback font: ${fallback.name}`);
            break;
          } catch (error) {
            continue;
          }
        }
      }
      if (fontLoaded) break;
    }
  }
  
  if (!fontLoaded) {
    console.warn('⚠️  No custom fonts loaded, using system default');
  }
  
  return fontFamily;
}

/**
 * Get today's Bangla date information
 * Converts UTC time to Bangladesh time (UTC+6)
 */
function getBanglaDateInfo() {
  // Get current time in Bangladesh (UTC+6)
  const now = new Date();
  const utcTime = now.getTime() + (now.getTimezoneOffset() * 60000);
  const bdTime = new Date(utcTime + (6 * 60 * 60 * 1000));

  // Use Bangladesh time for Bangla date calculation
  const banglaDay = getDay(bdTime, { format: 'D', calculationMethod: 'BD' });
  const banglaMonth = getMonth(bdTime, { format: 'MMMM', calculationMethod: 'BD' });
  const banglaYear = getYear(bdTime, { format: 'YYYY', calculationMethod: 'BD' });
  const banglaWeekday = getWeekDay(bdTime, { format: 'eeee', calculationMethod: 'BD' });

  // Get ordinal date
  const banglaDateOrdinal = getBanglaOrdinal(banglaDay);

  // Get season
  const banglaSeason = getBanglaSeason(banglaMonth);

  // Format English date for reference
  const englishDate = bdTime.toLocaleDateString('en-US', {
    day: '2-digit',
    month: 'long',
    year: 'numeric'
  });

  return {
    date: banglaDateOrdinal,
    month: banglaMonth,
    year: banglaYear,
    weekday: banglaWeekday,
    season: banglaSeason,
    englishDate,
    bdTime
  };
}

/**
 * Get profile information from Bluesky API
 */
async function getProfileInfo() {
  const handle = process.env.BLUESKY_HANDLE || process.env.BSKY_USERNAME || 'sayed.app';
  const cleanHandle = handle.includes('@') ? handle.split('@')[0] : handle;

  try {
    const response = await fetch(
      `https://public.api.bsky.app/xrpc/app.bsky.actor.getProfile?actor=${cleanHandle}`
    );

    if (response.ok) {
      const profile = await response.json();
      return {
        handle: profile.handle || cleanHandle,
        displayName: profile.displayName || cleanHandle,
        avatar: profile.avatar || null
      };
    } else {
      console.warn(`⚠️  Could not fetch profile from API: ${response.status}`);
    }
  } catch (error) {
    console.warn(`⚠️  Error fetching profile: ${error.message}`);
  }

  // Fallback to basic info
  return {
    handle: cleanHandle,
    displayName: cleanHandle,
    avatar: null
  };
}

/**
 * Download an image from URL
 */
async function downloadImage(url) {
  return new Promise((resolve, reject) => {
    https.get(url, (response) => {
      const chunks = [];
      response.on('data', (chunk) => chunks.push(chunk));
      response.on('end', () => resolve(Buffer.concat(chunks)));
      response.on('error', reject);
    }).on('error', reject);
  });
}

/**
 * Convert hex color to RGB values
 */
function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : { r: 0, g: 0, b: 0 };
}

/**
 * Create a dark-themed image with Bangla date information
 */
async function createBanglaDateImage(outputPath = 'bangla_date.png') {
  console.log('🔄 Generating Bangla date image...');

  // Load fonts
  const fontFamily = loadFonts();

  // Get Bangla date info
  const banglaDateInfo = getBanglaDateInfo();
  console.log(`📅 Date: ${banglaDateInfo.date} ${banglaDateInfo.month}, ${banglaDateInfo.year} বঙ্গাব্দ`);

  // Get profile info
  const profile = await getProfileInfo();

  // Create canvas
  const canvas = createCanvas(WIDTH, HEIGHT);
  const ctx = canvas.getContext('2d');

  // Fill background
  ctx.fillStyle = COLORS.bg;
  ctx.fillRect(0, 0, WIDTH, HEIGHT);

  // Card dimensions
  const cardMargin = 60;
  const cardWidth = WIDTH - (2 * cardMargin);
  const cardHeight = HEIGHT - (2 * cardMargin);

  // Draw card background with rounded corners
  ctx.fillStyle = COLORS.cardBg;
  ctx.strokeStyle = COLORS.border;
  ctx.lineWidth = 2;
  const radius = 20;
  ctx.beginPath();
  ctx.moveTo(cardMargin + radius, cardMargin);
  ctx.lineTo(WIDTH - cardMargin - radius, cardMargin);
  ctx.quadraticCurveTo(WIDTH - cardMargin, cardMargin, WIDTH - cardMargin, cardMargin + radius);
  ctx.lineTo(WIDTH - cardMargin, HEIGHT - cardMargin - radius);
  ctx.quadraticCurveTo(WIDTH - cardMargin, HEIGHT - cardMargin, WIDTH - cardMargin - radius, HEIGHT - cardMargin);
  ctx.lineTo(cardMargin + radius, HEIGHT - cardMargin);
  ctx.quadraticCurveTo(cardMargin, HEIGHT - cardMargin, cardMargin, HEIGHT - cardMargin - radius);
  ctx.lineTo(cardMargin, cardMargin + radius);
  ctx.quadraticCurveTo(cardMargin, cardMargin, cardMargin + radius, cardMargin);
  ctx.closePath();
  ctx.fill();
  ctx.stroke();

  // Header settings
  const headerY = 90;
  const headerPadding = 100;
  const avatarSize = 128;
  const logoSize = 128;

  // Calculate positions
  const avatarX = headerPadding;
  const textX = avatarX + avatarSize + 20;
  const textLine1Y = headerY;
  const textLine2Y = textLine1Y + 70;
  const avatarY = headerY + 5;
  const logoX = WIDTH - headerPadding - logoSize;
  const logoY = headerY + 5;

  // Draw avatar (placeholder circle or actual image)
  if (profile.avatar) {
    try {
      const avatarBuffer = await downloadImage(profile.avatar);
      const avatarImg = await loadImage(avatarBuffer);
      
      // Create circular clipping path
      ctx.save();
      ctx.beginPath();
      ctx.arc(avatarX + avatarSize / 2, avatarY + avatarSize / 2, avatarSize / 2, 0, Math.PI * 2);
      ctx.closePath();
      ctx.clip();
      ctx.drawImage(avatarImg, avatarX, avatarY, avatarSize, avatarSize);
      ctx.restore();
    } catch (error) {
      console.warn(`⚠️  Could not load avatar: ${error.message}`);
      // Draw placeholder circle
      ctx.fillStyle = COLORS.accent;
      ctx.strokeStyle = COLORS.textPrimary;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(avatarX + avatarSize / 2, avatarY + avatarSize / 2, avatarSize / 2, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    }
  } else {
    // Draw placeholder circle
    ctx.fillStyle = COLORS.accent;
    ctx.strokeStyle = COLORS.textPrimary;
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(avatarX + avatarSize / 2, avatarY + avatarSize / 2, avatarSize / 2, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
  }

  // Draw profile info text
  ctx.font = `${FONT_SIZES.small}px ${fontFamily}`;
  ctx.fillStyle = COLORS.textPrimary;
  ctx.fillText(profile.displayName, textX, textLine1Y + FONT_SIZES.small);

  ctx.fillStyle = COLORS.textSecondary;
  ctx.fillText(`@${profile.handle}`, textX, textLine2Y + FONT_SIZES.small);

  // Draw Bluesky logo
  const logoPath = path.join(__dirname, '../../fonts/bluesky_logo.png');
  let logoLoaded = false;

  // Try local file first
  if (fs.existsSync(logoPath)) {
    try {
      const logoImg = await loadImage(logoPath);
      ctx.drawImage(logoImg, logoX, logoY, logoSize, logoSize);
      logoLoaded = true;
    } catch (error) {
      console.warn(`⚠️  Could not load local logo: ${error.message}`);
    }
  }

  // If local file didn't work, try downloading
  if (!logoLoaded) {
    try {
      const logoBuffer = await downloadImage('https://bsky.app/static/apple-touch-icon.png');
      const logoImg = await loadImage(logoBuffer);
      ctx.drawImage(logoImg, logoX, logoY, logoSize, logoSize);
      logoLoaded = true;
    } catch (error) {
      console.warn(`⚠️  Could not download logo: ${error.message}`);
    }
  }

  // Fallback if nothing worked
  if (!logoLoaded) {
    console.warn('⚠️  Using fallback circle logo');
    ctx.fillStyle = COLORS.accent;
    ctx.beginPath();
    ctx.arc(logoX + logoSize / 2, logoY + logoSize / 2, logoSize / 2, 0, Math.PI * 2);
    ctx.fill();
  }

  // Content positioning - center block in the middle
  const centerX = WIDTH / 2;
  const lineHeightDate = FONT_SIZES.date * 1.2;
  const lineHeightInfo = FONT_SIZES.info * 1.2;
  const extraSpacing = 30;
  const totalHeight = lineHeightDate + lineHeightDate + extraSpacing + lineHeightInfo;
  const blockTop = (HEIGHT - totalHeight) / 2;

  // Line 1: date + month with trailing comma
  const line1 = `${banglaDateInfo.date} ${banglaDateInfo.month},`;
  ctx.font = `${FONT_SIZES.date}px ${fontFamily}`;
  ctx.fillStyle = COLORS.textPrimary;
  ctx.textAlign = 'center';
  ctx.textBaseline = 'top';
  const y1 = blockTop;
  ctx.fillText(line1, centerX, y1);

  // Line 2: year + বঙ্গাব্দ
  const line2 = `${banglaDateInfo.year} বঙ্গাব্দ`;
  const y2 = y1 + lineHeightDate;
  ctx.fillText(line2, centerX, y2);

  // Line 3: combined weekday and season with highlights
  const prefix1 = 'বারঃ ';
  const weekday = banglaDateInfo.weekday;
  const comma = ', ';
  const prefix2 = 'ঋতুঃ ';
  const season = banglaDateInfo.season;

  // Set font for line 3
  ctx.font = `${FONT_SIZES.info}px ${fontFamily}`;
  ctx.textAlign = 'left';

  // Measure segments
  const p1W = ctx.measureText(prefix1).width;
  const wdW = ctx.measureText(weekday).width;
  const commaW = ctx.measureText(comma).width;
  const p2W = ctx.measureText(prefix2).width;
  const seasonW = ctx.measureText(season).width;

  const totalW = p1W + wdW + commaW + p2W + seasonW;
  const xStart = centerX - totalW / 2;
  const y3 = y2 + lineHeightDate + extraSpacing;

  // Draw prefix1
  ctx.fillStyle = COLORS.textSecondary;
  ctx.fillText(prefix1, xStart, y3);
  let xCursor = xStart + p1W;

  // Draw weekday (highlight)
  ctx.fillStyle = COLORS.accent;
  ctx.fillText(weekday, xCursor, y3);
  xCursor += wdW;

  // Draw comma
  ctx.fillStyle = COLORS.textSecondary;
  ctx.fillText(comma, xCursor, y3);
  xCursor += commaW;

  // Draw prefix2
  ctx.fillText(prefix2, xCursor, y3);
  xCursor += p2W;

  // Draw season (highlight)
  ctx.fillStyle = COLORS.accent;
  ctx.fillText(season, xCursor, y3);

  // Convert canvas to buffer and save
  const buffer = canvas.toBuffer('image/png');
  fs.writeFileSync(outputPath, buffer);
  console.log(`✅ Image saved successfully: ${outputPath}`);

  // Compose date_text for caption
  const captionDateText = `${banglaDateInfo.date} ${banglaDateInfo.month}, ${banglaDateInfo.year} বঙ্গাব্দ`;
  return { outputPath, captionDateText, banglaDateInfo };
}

/**
 * Post the image to Bluesky with rich text facets for hashtags
 */
async function postToBluesky(imagePath, dateText, banglaDateInfo) {
  console.log('🔄 Posting to Bluesky...');

  // Get credentials from environment
  const handle = process.env.BLUESKY_HANDLE || process.env.BSKY_USERNAME;
  const password = process.env.BLUESKY_PASSWORD || process.env.BSKY_APP_PASSWORD;

  if (!handle || !password) {
    console.warn('⚠️  Bluesky credentials not found in environment variables');
    console.log('Skipping Bluesky post...');
    return false;
  }

  try {
    // Initialize agent
    const agent = new AtpAgent({ service: 'https://bsky.social' });

    // Login
    await agent.login({ identifier: handle, password });
    console.log('✅ Logged in to Bluesky');

    // Read image
    const imageBuffer = fs.readFileSync(imagePath);

    // Upload image
    const uploadResponse = await agent.uploadBlob(imageBuffer, {
      encoding: 'image/png'
    });
    console.log('✅ Image uploaded');

    // Create post text with new format
    const postText = `আজ রোজ ${banglaDateInfo.weekday},\n${dateText}\nএবং ${banglaDateInfo.season}কাল\n\n#Bangladesh #Bangla #বাংলাদেশ #বাংলা #বাংলাতারিখ #তারিখ #date #BanglaDate`;

    // Create rich text for facets
    const rt = new RichText({ text: postText });
    await rt.detectFacets(agent);

    // Create post with image
    const postRecord = {
      text: rt.text,
      facets: rt.facets,
      embed: {
        $type: 'app.bsky.embed.images',
        images: [{
          alt: `আজকের বাংলা তারিখ: ${dateText}`,
          image: uploadResponse.data.blob
        }]
      },
      createdAt: new Date().toISOString()
    };

    const response = await agent.post(postRecord);
    console.log(`✅ Posted to Bluesky: ${response.uri}`);
    return true;
  } catch (error) {
    console.error(`❌ Error posting to Bluesky: ${error.message}`);
    console.error(error.stack);
    return false;
  }
}

/**
 * Main function
 */
async function main() {
  try {
    console.log('🔄 Starting Bangla date image generator...');

    // Create output directory if it doesn't exist
    const outputDir = path.join(__dirname, '../../output');
    if (!fs.existsSync(outputDir)) {
      fs.mkdirSync(outputDir, { recursive: true });
    }

    // Generate filename with timestamp
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0] + '_' + 
                      new Date().toTimeString().split(' ')[0].replace(/:/g, '');
    const outputPath = path.join(outputDir, `bangla_date_${timestamp}.png`);

    // Create image
    const { captionDateText, banglaDateInfo } = await createBanglaDateImage(outputPath);

    // Check if we should post to Bluesky
    const shouldPost = process.env.POST_TO_BLUESKY?.toLowerCase() === 'true';

    if (shouldPost) {
      console.log('\n🔄 Posting to Bluesky...');
      await postToBluesky(outputPath, captionDateText, banglaDateInfo);
    } else {
      console.log('\n⚠️  POST_TO_BLUESKY not set to \'true\', skipping Bluesky post');
      console.log('📝 To post to Bluesky, set POST_TO_BLUESKY=true in your .env file');
    }

    console.log('\n✨ Done!');
  } catch (error) {
    console.error('❌ Error:', error.message);
    console.error(error.stack);
    process.exit(1);
  }
}

// Run main function
main();
