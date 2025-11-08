/**
 * Utility functions for Bangla date processing
 */

/**
 * Bangla ordinal suffixes mapping
 * Based on Bengali ordinal number system
 */
const BANGLA_ORDINALS = {
  '১': '১লা',
  '২': '২রা',
  '৩': '৩রা',
  '৪': '৪ঠা',
  '৫': '৫ই',
  '৬': '৬ই',
  '৭': '৭ই',
  '৮': '৮ই',
  '৯': '৯ই',
  '১০': '১০ই',
  '১১': '১১ই',
  '১২': '১২ই',
  '১৩': '১৩ই',
  '১৪': '১৪ই',
  '১৫': '১৫ই',
  '১৬': '১৬ই',
  '১৭': '১৭ই',
  '১৮': '১৮ই',
  '১৯': '১৯শে',
  '২০': '২০শে',
  '২১': '২১শে',
  '২২': '২২শে',
  '২৩': '২৩শে',
  '২৪': '২৪শে',
  '২৫': '২৫শে',
  '২৬': '২৬শে',
  '২৭': '২৭শে',
  '২৮': '২৮শে',
  '২৯': '২৯শে',
  '৩০': '৩০শে',
  '৩১': '৩১শে'
};

/**
 * Bangla months to season mapping
 * 6 seasons (ঋতু) in Bengali calendar
 */
const BANGLA_SEASONS = {
  'বৈশাখ': 'গ্রীষ্ম',
  'জ্যৈষ্ঠ': 'গ্রীষ্ম',
  'আষাঢ়': 'বর্ষা',
  'শ্রাবণ': 'বর্ষা',
  'ভাদ্র': 'শরৎ',
  'আশ্বিন': 'শরৎ',
  'কার্তিক': 'হেমন্ত',
  'অগ্রহায়ণ': 'হেমন্ত',
  'পৌষ': 'শীত',
  'মাঘ': 'শীত',
  'ফাল্গুন': 'বসন্ত',
  'চৈত্র': 'বসন্ত'
};

/**
 * Convert Bangla date number to ordinal form
 * @param {string} banglaDate - Bangla date string (e.g., '২৩')
 * @returns {string} Ordinal form (e.g., '২৩শে')
 */
export function getBanglaOrdinal(banglaDate) {
  return BANGLA_ORDINALS[banglaDate] || banglaDate;
}

/**
 * Get season (ঋতু) for a Bangla month
 * @param {string} banglaMonth - Bangla month name (e.g., 'কার্তিক')
 * @returns {string} Season name (e.g., 'হেমন্ত')
 */
export function getBanglaSeason(banglaMonth) {
  return BANGLA_SEASONS[banglaMonth] || '';
}

/**
 * Convert UTC time to Bangladesh time (UTC+6)
 * @param {Date} date - JavaScript Date object (default: now)
 * @returns {Date} Date object adjusted to Bangladesh timezone
 */
export function toBangladeshTime(date = new Date()) {
  // Get UTC time in milliseconds
  const utcTime = date.getTime();
  
  // Bangladesh is UTC+6
  const bdOffset = 6 * 60 * 60 * 1000;
  
  // Create new date with BD timezone offset
  return new Date(utcTime + bdOffset);
}

/**
 * Format number with leading zero
 * @param {number} num - Number to format
 * @returns {string} Formatted number
 */
export function padZero(num) {
  return num.toString().padStart(2, '0');
}
