/**
 * AI Newsletter - Google Apps Script
 * Personalized weekly digest of AI news
 *
 * PROFILE: Business/Management focused
 * INTERESTS: Generative AI, AI for business, industry trends
 * DEPTH: High-level summaries
 * EXCLUDES: Hype/speculation, stock tips, policy/regulation
 *
 * Setup:
 * 1. Copy this entire script into Google Apps Script (script.google.com)
 * 2. Run sendAINewsletter() manually to test
 * 3. Run setupWeeklyTrigger() once to schedule weekly emails
 */

// ============ CONFIGURATION ============
const CONFIG = {
  recipientEmail: "andries.fluit@gmail.com",
  senderName: "AI Weekly Digest",

  // RSS feeds focused on business/generative AI (removed policy-heavy sources)
  feeds: [
    // Major Labs - Product announcements
    {
      name: "OpenAI Blog",
      url: "https://openai.com/blog/rss/",
      category: "Product Launches",
      weight: 1.5
    },
    {
      name: "Anthropic News",
      url: "https://www.anthropic.com/news/rss",
      category: "Product Launches",
      weight: 1.5
    },
    {
      name: "Google AI Blog",
      url: "https://blog.google/technology/ai/rss/",
      category: "Product Launches",
      weight: 1.3
    },
    {
      name: "DeepMind Blog",
      url: "https://deepmind.google/blog/rss.xml",
      category: "Product Launches",
      weight: 1.2
    },
    // Industry News
    {
      name: "TechCrunch AI",
      url: "https://techcrunch.com/category/artificial-intelligence/feed/",
      category: "Industry News",
      weight: 1.0
    },
    {
      name: "VentureBeat AI",
      url: "https://venturebeat.com/category/ai/feed/",
      category: "Industry News",
      weight: 1.0
    },
    {
      name: "The Verge AI",
      url: "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
      category: "Industry News",
      weight: 0.9
    },
    {
      name: "Wired AI",
      url: "https://www.wired.com/feed/tag/ai/latest/rss",
      category: "Industry News",
      weight: 0.9
    },
    // Business/Enterprise focused
    {
      name: "MIT Technology Review - AI",
      url: "https://www.technologyreview.com/topic/artificial-intelligence/feed",
      category: "Analysis & Trends",
      weight: 1.4
    },
    {
      name: "Harvard Business Review",
      url: "https://hbr.org/topic/technology/feed",
      category: "Business Strategy",
      weight: 1.3
    },
    // Tools & Platforms
    {
      name: "Hugging Face Blog",
      url: "https://huggingface.co/blog/feed.xml",
      category: "Tools & Platforms",
      weight: 0.8
    }
  ],

  // How many items to fetch per feed before filtering
  itemsPerFeed: 10,

  // Final number of articles in newsletter (after filtering)
  maxTotalItems: 15,

  // How many days back to look
  daysToLookBack: 7
};

// ============ RELEVANCE SCORING ============
const SCORING = {
  // HIGH VALUE keywords (business/generative AI focused)
  boost: [
    // Generative AI products & tools
    "chatgpt", "claude", "gemini", "copilot", "midjourney", "dall-e", "sora",
    "gpt-4", "gpt-5", "opus", "sonnet", "llama",
    // Business applications
    "enterprise", "business", "productivity", "workflow", "automation",
    "roi", "adoption", "implementation", "use case", "case study",
    "customer", "revenue", "efficiency", "cost saving",
    // AI agents & assistants
    "ai agent", "autonomous", "assistant", "copilot", "agentic",
    // Practical applications
    "launch", "release", "announce", "available", "rolling out",
    "partnership", "integration", "api", "platform",
    // Industry trends
    "market", "growth", "trend", "forecast", "adoption rate",
    "startup", "funding round", "acquisition",
    // Creative/Generative
    "image generation", "video generation", "text-to", "generative",
    "content creation", "creative ai"
  ],

  // PENALTY keywords (exclude hype, stocks, policy)
  penalize: [
    // Hype & speculation
    "agi", "artificial general intelligence", "superintelligence", "singularity",
    "existential risk", "doom", "takeover", "sentient", "conscious ai",
    "will replace", "end of", "death of", "revolution",
    "insane", "mind-blowing", "game-changer", "disruption",
    // Stock/Investment focused
    "stock price", "share price", "market cap", "valuation",
    "buy rating", "sell rating", "investor", "ipo", "earnings",
    "nasdaq", "nyse", "s&p", "portfolio", "dividend",
    // Policy/Regulation
    "regulation", "regulatory", "legislation", "congress", "senate",
    "eu ai act", "executive order", "compliance", "lawsuit", "sued",
    "antitrust", "ftc", "doj", "policy", "government",
    // Technical jargon (too deep)
    "arxiv", "paper", "benchmark", "parameters", "tokens per second",
    "fine-tuning", "rlhf", "transformer architecture", "attention mechanism"
  ],

  // Bonus for titles that suggest practical/actionable content
  practicalPatterns: [
    /how to/i,
    /guide/i,
    /tips/i,
    /best practices/i,
    /\d+ ways/i,
    /what .* means for/i,
    /why .* matters/i,
    /launches/i,
    /announces/i,
    /introduces/i,
    /now available/i,
    /rolls out/i
  ]
};

// ============ MAIN FUNCTIONS ============

/**
 * Main function - fetches, filters, and sends the newsletter
 */
function sendAINewsletter() {
  try {
    Logger.log("Starting AI Newsletter generation...");

    // Fetch all articles
    const allArticles = fetchAllFeeds();
    Logger.log(`Fetched ${allArticles.length} articles total`);

    if (allArticles.length === 0) {
      Logger.log("No articles found. Skipping newsletter.");
      return;
    }

    // Score and filter articles
    const scoredArticles = allArticles.map(article => ({
      ...article,
      score: calculateRelevanceScore(article)
    }));

    // Sort by score and take top articles
    scoredArticles.sort((a, b) => b.score - a.score);
    const topArticles = scoredArticles
      .filter(a => a.score > 0) // Remove negative-scored articles
      .slice(0, CONFIG.maxTotalItems);

    Logger.log(`Selected ${topArticles.length} top articles after filtering`);

    if (topArticles.length === 0) {
      Logger.log("No relevant articles after filtering. Skipping newsletter.");
      return;
    }

    // Generate and send
    const html = generateNewsletterHTML(topArticles);
    const subject = `🤖 AI Weekly Digest - ${formatDate(new Date())}`;

    GmailApp.sendEmail(CONFIG.recipientEmail, subject, "", {
      htmlBody: html,
      name: CONFIG.senderName
    });

    Logger.log(`Newsletter sent successfully to ${CONFIG.recipientEmail}`);

  } catch (error) {
    Logger.log(`Error sending newsletter: ${error.message}`);
    GmailApp.sendEmail(CONFIG.recipientEmail, "AI Newsletter Error",
      `The AI newsletter failed to send. Error: ${error.message}`);
  }
}

/**
 * Calculate relevance score for an article
 */
function calculateRelevanceScore(article) {
  const text = `${article.title} ${article.description}`.toLowerCase();
  let score = article.sourceWeight || 1.0;

  // Apply boost keywords
  SCORING.boost.forEach(keyword => {
    if (text.includes(keyword.toLowerCase())) {
      score += 0.5;
    }
  });

  // Apply penalty keywords
  SCORING.penalize.forEach(keyword => {
    if (text.includes(keyword.toLowerCase())) {
      score -= 0.8;
    }
  });

  // Bonus for practical/actionable titles
  SCORING.practicalPatterns.forEach(pattern => {
    if (pattern.test(article.title)) {
      score += 0.3;
    }
  });

  // Slight recency bonus (newer = better)
  const ageInDays = (new Date() - article.date) / (1000 * 60 * 60 * 24);
  if (ageInDays < 2) {
    score += 0.3;
  } else if (ageInDays < 4) {
    score += 0.1;
  }

  return score;
}

/**
 * Set up weekly trigger - RUN THIS ONCE
 * Sends every Sunday at 9 AM
 */
function setupWeeklyTrigger() {
  // Remove existing triggers
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => {
    if (trigger.getHandlerFunction() === 'sendAINewsletter') {
      ScriptApp.deleteTrigger(trigger);
    }
  });

  // Create new weekly trigger
  ScriptApp.newTrigger('sendAINewsletter')
    .timeBased()
    .onWeekDay(ScriptApp.WeekDay.SUNDAY)
    .atHour(9)
    .create();

  Logger.log("Weekly trigger set! Newsletter sends every Sunday at 9 AM.");
}

/**
 * Remove all triggers - run to stop the newsletter
 */
function removeAllTriggers() {
  const triggers = ScriptApp.getProjectTriggers();
  triggers.forEach(trigger => ScriptApp.deleteTrigger(trigger));
  Logger.log("All triggers removed.");
}

// ============ FEED FETCHING ============

function fetchAllFeeds() {
  const allArticles = [];
  const cutoffDate = new Date();
  cutoffDate.setDate(cutoffDate.getDate() - CONFIG.daysToLookBack);

  CONFIG.feeds.forEach(feed => {
    try {
      const articles = fetchFeed(feed, cutoffDate);
      allArticles.push(...articles);
      Logger.log(`${feed.name}: ${articles.length} articles`);
    } catch (error) {
      Logger.log(`Error fetching ${feed.name}: ${error.message}`);
    }
  });

  return allArticles;
}

function fetchFeed(feed, cutoffDate) {
  const response = UrlFetchApp.fetch(feed.url, {
    muteHttpExceptions: true,
    followRedirects: true
  });

  if (response.getResponseCode() !== 200) {
    throw new Error(`HTTP ${response.getResponseCode()}`);
  }

  const xml = response.getContentText();
  const document = XmlService.parse(xml);
  const root = document.getRootElement();

  const articles = [];
  const items = findItems(root);

  items.slice(0, CONFIG.itemsPerFeed).forEach(item => {
    try {
      const article = parseItem(item, feed);
      if (article && article.date >= cutoffDate) {
        articles.push(article);
      }
    } catch (e) {
      // Skip malformed items
    }
  });

  return articles;
}

function findItems(root) {
  const ns = root.getNamespace();

  // Try RSS format
  let items = root.getChildren('channel', ns);
  if (items.length > 0) {
    items = items[0].getChildren('item', ns);
    if (items.length > 0) return items;
    items = root.getChildren('channel')[0]?.getChildren('item') || [];
    if (items.length > 0) return items;
  }

  // Try Atom format
  items = root.getChildren('entry', ns);
  if (items.length > 0) return items;
  items = root.getChildren('entry');
  if (items.length > 0) return items;

  // Direct item children
  items = root.getChildren('item', ns);
  if (items.length > 0) return items;
  return root.getChildren('item');
}

function parseItem(item, feed) {
  const ns = item.getNamespace();

  let title = getChildText(item, 'title', ns) || getChildText(item, 'title');
  if (!title) return null;

  let link = getChildText(item, 'link', ns) || getChildText(item, 'link');
  if (!link) {
    const linkEl = item.getChild('link', ns) || item.getChild('link');
    if (linkEl) {
      link = linkEl.getAttribute('href')?.getValue();
    }
  }
  if (!link) return null;

  let description = getChildText(item, 'description', ns) ||
                    getChildText(item, 'description') ||
                    getChildText(item, 'summary', ns) ||
                    getChildText(item, 'summary') ||
                    getChildText(item, 'content', ns) ||
                    getChildText(item, 'content') || "";

  description = cleanHTML(description);
  if (description.length > 250) {
    description = description.substring(0, 247) + "...";
  }

  let dateStr = getChildText(item, 'pubDate', ns) ||
                getChildText(item, 'pubDate') ||
                getChildText(item, 'published', ns) ||
                getChildText(item, 'published') ||
                getChildText(item, 'updated', ns) ||
                getChildText(item, 'updated');

  let date = dateStr ? new Date(dateStr) : new Date();
  if (isNaN(date.getTime())) date = new Date();

  return {
    title: cleanHTML(title),
    link: link,
    description: description,
    date: date,
    source: feed.name,
    category: feed.category,
    sourceWeight: feed.weight || 1.0
  };
}

function getChildText(parent, childName, ns) {
  const child = ns ? parent.getChild(childName, ns) : parent.getChild(childName);
  return child ? child.getText() : null;
}

function cleanHTML(text) {
  if (!text) return "";
  text = text.replace(/<[^>]*>/g, '');
  text = text.replace(/&amp;/g, '&')
             .replace(/&lt;/g, '<')
             .replace(/&gt;/g, '>')
             .replace(/&quot;/g, '"')
             .replace(/&#39;/g, "'")
             .replace(/&nbsp;/g, ' ');
  return text.replace(/\s+/g, ' ').trim();
}

function formatDate(date) {
  return date.toLocaleDateString('en-US', {
    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
  });
}

function formatDateShort(date) {
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

// ============ HTML GENERATION ============

function generateNewsletterHTML(articles) {
  // Group by category
  const categories = {};
  articles.forEach(article => {
    if (!categories[article.category]) {
      categories[article.category] = [];
    }
    categories[article.category].push(article);
  });

  const categoryOrder = [
    "Product Launches",
    "Business Strategy",
    "Analysis & Trends",
    "Industry News",
    "Tools & Platforms"
  ];

  let articlesHTML = "";

  categoryOrder.forEach(category => {
    if (categories[category] && categories[category].length > 0) {
      articlesHTML += `
        <tr>
          <td style="padding: 25px 0 12px 0;">
            <h2 style="color: #1a1a2e; font-size: 16px; font-weight: 700; margin: 0; text-transform: uppercase; letter-spacing: 1px; padding-bottom: 8px; border-bottom: 3px solid #4a90d9;">
              ${category}
            </h2>
          </td>
        </tr>
      `;

      categories[category].forEach(article => {
        articlesHTML += `
          <tr>
            <td style="padding: 16px 0; border-bottom: 1px solid #eee;">
              <a href="${article.link}" style="color: #1a1a2e; text-decoration: none; font-size: 17px; font-weight: 600; line-height: 1.4; display: block;">
                ${article.title}
              </a>
              <p style="color: #555; font-size: 14px; margin: 10px 0 8px 0; line-height: 1.6;">
                ${article.description}
              </p>
              <p style="color: #888; font-size: 12px; margin: 0;">
                <span style="color: #4a90d9; font-weight: 500;">${article.source}</span> · ${formatDateShort(article.date)}
              </p>
            </td>
          </tr>
        `;
      });
    }
  });

  const today = new Date();
  const weekAgo = new Date(today);
  weekAgo.setDate(weekAgo.getDate() - 7);

  return `
<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
</head>
<body style="margin: 0; padding: 0; background-color: #f0f2f5; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background-color: #f0f2f5; padding: 30px 0;">
    <tr>
      <td align="center">
        <table width="600" cellpadding="0" cellspacing="0" style="background-color: #ffffff; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="background: linear-gradient(135deg, #1a1a2e 0%, #2d5a8a 100%); padding: 35px 30px; text-align: center;">
              <h1 style="color: #ffffff; font-size: 26px; font-weight: 700; margin: 0; letter-spacing: -0.5px;">
                🤖 AI Weekly Digest
              </h1>
              <p style="color: rgba(255,255,255,0.85); font-size: 14px; margin: 12px 0 0 0;">
                ${formatDateShort(weekAgo)} – ${formatDateShort(today)}
              </p>
            </td>
          </tr>

          <!-- Profile badge -->
          <tr>
            <td style="padding: 20px 30px 0 30px;">
              <table cellpadding="0" cellspacing="0" style="background-color: #f8f9fa; border-radius: 8px; padding: 12px 16px;">
                <tr>
                  <td>
                    <p style="color: #666; font-size: 12px; margin: 0;">
                      <strong style="color: #4a90d9;">Curated for:</strong> Business & Management · Generative AI · Industry Trends
                    </p>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- Articles -->
          <tr>
            <td style="padding: 10px 30px 20px 30px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                ${articlesHTML}
              </table>
            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="padding: 25px 30px; background-color: #f8f9fa; text-align: center; border-top: 1px solid #eee;">
              <p style="color: #999; font-size: 11px; margin: 0; line-height: 1.6;">
                Automatically curated from OpenAI, Anthropic, Google AI, MIT Tech Review, TechCrunch & more.<br>
                Filtered to exclude: hype/speculation, stock tips, policy/regulation.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>
  `;
}
