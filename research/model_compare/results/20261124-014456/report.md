# Model comparison — Dallas florist prompts

Run 24 Nov 2026 01:44 · 3 runs per prompt · 117 calls in 1143s · names extracted and checked with gemini-3.8-flash

| Model | Web? | Overlap with apps | Run-to-run | Names/answer | Real & operating | "near me" | Avg s | Errors |
|---|---|---|---|---|---|---|---|---|
| openrouter:anthropic/claude-haiku-5.5:online | yes | 27% | 61% | 11.6 | 95% | – | 11 | 4/9 |
| gemini:gemini-3.8-flash [maps_dallas] | yes | 24% | 71% | 5.4 | 100% | 15/15 Dallas | 19 | 0/9 |
| gemini:gemini-3.8-flash [search] | yes | 24% | 63% | 9.0 | 95% | 21/21 Dallas | 15 | 0/9 |
| openrouter:openai/gpt-5-mini:online | yes | 21% | – | 8.0 | 100% | – | 22 | 8/9 |
| nvidia:moonshotai/kimi-k3.1-pro | no | 17% | 66% | 3.0 | 88% | asks / no names | 175 | 1/9 |
| openrouter:perplexity/sonar | yes | 16% | 41% | 9.0 | 95% | 2/5 Dallas | 6 | 0/9 |
| gemini:gemini-3.8-flash [memory] | no | 15% | 30% | 5.2 | 91% | 3/3 Dallas | 16 | 0/9 |
| nvidia:minimaxai/minimax-m3.1-flash | no | 4% | 17% | 10.9 | 85% | 5/5 Dallas | 33 | 0/9 |
| nvidia:nvidia/nemotron-3-ultra-550b-a55b | no | 3% | 24% | 14.9 | 81% | 8/8 Dallas | 33 | 0/9 |
| nvidia:mistralai/mistral-large-4-1t-a52b | no | 3% | 32% | 8.4 | 83% | 4/4 Dallas | 126 | 2/9 |
| nvidia:google/gemma-4-31b-it | no | 2% | 58% | 7.9 | 85% | asks / no names | 109 | 2/9 |
| nvidia:nvidia/nemotron-3.5-lightning-30b-a3b | no | 2% | 27% | 4.2 | 92% | asks / no names | 7 | 0/9 |
| openrouter:openai/gpt-5-mini | no | – | – | – | – | – | – | 9/9 |

*Overlap with apps*: share of businesses in common with each app answer (ChatGPT, Google AI Mode, Copilot, Bing) for the two Dallas prompts, averaged. *Real & operating*: share of named businesses confirmed as open Dallas-area florists (seen in an app or in Google Maps, or checked with Google Search).

## Named businesses that are not real, open Dallas florists

| Name | Status | Named by |
|---|---|---|
| Cebolla Fine Flowers | closed | anthropic/claude-haiku-5.5:online, gemini-3.8-flash [memory], gemini-3.8-flash [search], moonshotai/kimi-k3.1-pro |
| Randy's Flowers | closed | nvidia/nemotron-3-ultra-550b-a55b |
| Freesia | closed | perplexity/sonar |
| DoorDash | not_florist | gemini-3.8-flash [memory], gemini-3.8-flash [search], google/gemma-4-31b-it, minimaxai/minimax-m3.1-flash, mistralai/mis |
| Whole Foods | not_florist | gemini-3.8-flash [memory], gemini-3.8-flash [search], google/gemma-4-31b-it, minimaxai/minimax-m3.1-flash, mistralai/mis |
| Flower Child | not_florist | google/gemma-4-31b-it, mistralai/mistral-large-4-1t-a52b, nvidia/nemotron-3-ultra-550b-a55b |
| Dempsey's | not_florist | mistralai/mistral-large-4-1t-a52b |
| Fleurs de Ville | not_florist | nvidia/nemotron-3-ultra-550b-a55b |
| CB2 | not_florist | nvidia/nemotron-3-ultra-550b-a55b |
| Blooming Colors | not_florist | minimaxai/minimax-m3.1-flash |
| Noble & Co. | not_florist | minimaxai/minimax-m3.1-flash |
| Flowers for Friends | not_florist | google/gemma-4-31b-it |
| Holly Poppy | not_found | mistralai/mistral-large-4-1t-a52b |
| Holly Pappas | not_found | mistralai/mistral-large-4-1t-a52b |
| The Dried Florist | not_found | nvidia/nemotron-3-ultra-550b-a55b |
| Deep Ellum Florist | not_found | nvidia/nemotron-3-ultra-550b-a55b |
| The Flower Shop FW | not_found | nvidia/nemotron-3-ultra-550b-a55b |
| Florence's Garden | not_found | minimaxai/minimax-m3.1-flash, nvidia/nemotron-3.5-lightning-30b-a3b |
| Bumgarner Florist | not_found | minimaxai/minimax-m3.1-flash |
| Luna & Grove | not_found | minimaxai/minimax-m3.1-flash |
| OrderFlowers | not_found | minimaxai/minimax-m3.1-flash |
| Flower Shop of Dallas | not_found | google/gemma-4-31b-it |
| Bellarosa Flowers | not_in_dallas | gemini-3.8-flash [memory] |
| Belen Flowers | not_in_dallas | gemini-3.8-flash [memory] |
| Blush & Bloom | not_in_dallas | mistralai/mistral-large-4-1t-a52b |
| Wildflowers | not_in_dallas | mistralai/mistral-large-4-1t-a52b, nvidia/nemotron-3-ultra-550b-a55b |
| The Flower Bar | not_in_dallas | anthropic/claude-haiku-5.5:online, mistralai/mistral-large-4-1t-a52b, nvidia/nemotron-3-ultra-550b-a55b, perplexity/sona |
| Bachman’s | not_in_dallas | nvidia/nemotron-3-ultra-550b-a55b |
| J. Morris Flowers | not_in_dallas | nvidia/nemotron-3-ultra-550b-a55b |
| Lavender & Lace | not_in_dallas | nvidia/nemotron-3-ultra-550b-a55b |
| Avondale Florist | not_in_dallas | nvidia/nemotron-3-ultra-550b-a55b |
| Bloom & Grow | not_in_dallas | nvidia/nemotron-3-ultra-550b-a55b, nvidia/nemotron-3.5-lightning-30b-a3b |
| Bella Fiori | not_in_dallas | nvidia/nemotron-3.5-lightning-30b-a3b |
| Lacy's Florist | not_in_dallas | minimaxai/minimax-m3.1-flash |
| G's Florist | not_in_dallas | minimaxai/minimax-m3.1-flash |
| Posh Florist | not_in_dallas | minimaxai/minimax-m3.1-flash |
| Blooming Rose Florist | not_in_dallas | minimaxai/minimax-m3.1-flash |
| Bloom & Wild | not_in_dallas | minimaxai/minimax-m3.1-flash |
| Highland Park Florist | not_in_dallas | minimaxai/minimax-m3.1-flash |
| Lee's Florist | not_in_dallas | minimaxai/minimax-m3.1-flash |
| Village Flower Shop | not_in_dallas | minimaxai/minimax-m3.1-flash |
| Flowers by Design | not_in_dallas | google/gemma-4-31b-it |
| Confucius Florist | not_in_dallas | perplexity/sonar |
| Isabel Florist | not_in_dallas | perplexity/sonar |

## Usage and cost

| Purpose | Calls | Tokens in | Tokens out (incl. thinking) | Search grounding | Maps grounding | Cost (USD) |
|---|---|---|---|---|---|---|
| answers (openrouter) | 15 | 106,882 | 16,366 | – | – | $0.1486 (reported) |
| name extraction (gemini) | 91 | 61,890 | 83,383 | – | – | $0.3591 |
| answers (gemini) | 27 | 1,949 | 35,408 | 9 | 9 | $0.1342 |
| answers (nvidia) | 49 | 3,009 | 50,541 | – | – | free credits |
| business check (gemini) | 5 | 37,146 | 48,546 | 5 | – | $0.2099 |

**Total: $0.8519** in tokens. Plus 23 grounded Gemini requests: free within the first 5,000 per month per tool, then $14/1,000 (= $0.32 if the free allowance is used up). Gemini prices: $0.75/M in, $3.75/M out (paid tier, until 31 Dec 2026).

## Answers per prompt

### best florists in Dallas

- **gemini:gemini-3.8-flash [memory]** run 1: Dr. Delphinium Designs & Events, Avant Garden, Grange Hall, DIRT Flowers, Park Cities Petals, The T Shop, Groovy Floral Co., Haute Floral
- **gemini:gemini-3.8-flash [memory]** run 2: Dirt Flowers, Avant Garden, Dr Delphinium Designs & Events, Cebolla Fine Flowers, McShan Florist, Park Cities Petals
- **gemini:gemini-3.8-flash [memory]** run 3: Dr. Delphinium Designs & Events, Avant Garden, Grange Hall, Dirt Flowers, Something Pretty Floral, McShan Florist
- **gemini:gemini-3.8-flash [search]** run 1: Dr. Delphinium Designs & Events, Avant Garden, DIRT Flowers, Twelve Thirty Four, Urban Flower / Grange Hall, McShan Florist, In Bloom Flowers, The T Shop, Park Cities Petals
- **gemini:gemini-3.8-flash [search]** run 2: Avant Garden, Park Cities Petals, DIRT Flowers, Cebolla Fine Flowers, Dr Delphinium Designs & Events, McShan Florist, In Bloom Flowers on Mockingbird, The T Shop, PRESCH Petals
- **gemini:gemini-3.8-flash [search]** run 3: Avant Garden, Dr. Delphinium Designs & Events, DIRT Flowers, Twelve Thirty Four by Patricio Rivera, Grange Hall, McShan Florist, Lane Florist
- **gemini:gemini-3.8-flash [maps_dallas]** run 1: McShan Florist, Dr Delphinium Designs & Events, French Florist, Designs East Florist & Interior, PRESCH Petals, In Bloom Flowers
- **gemini:gemini-3.8-flash [maps_dallas]** run 2: McShan Florist, Dr Delphinium Designs & Events, French Florist, Park Cities Petals, Designs East Florist & Interior, PRESCH Petals
- **gemini:gemini-3.8-flash [maps_dallas]** run 3: McShan Florist, In Bloom Flowers, Dr Delphinium Designs & Events, Avant Garden, French Florist, PRESCH Petals, Designs East Florist & Interior
- **nvidia:moonshotai/kimi-k3.1-pro** run 1: Dr Delphinium Designs & Events, McShan Florist, Cebolla Fine Flowers, Avant Garden, R Love Floral Designs
- **nvidia:moonshotai/kimi-k3.1-pro** run 2: McShan Florist, Dr Delphinium Designs & Events, Cebolla Fine Flowers, Avant Garden, Kate Foley Designs
- **nvidia:moonshotai/kimi-k3.1-pro** run 3: ERROR ReadTimeout
- **nvidia:mistralai/mistral-large-4-1t-a52b** run 1: ERROR ReadTimeout
- **nvidia:mistralai/mistral-large-4-1t-a52b** run 2: ERROR ReadTimeout
- **nvidia:mistralai/mistral-large-4-1t-a52b** run 3: Holly Poppy, Poteet Victory, Stems, Blush & Bloom, Flower Child, Moss, Wildflowers, Dallas Flower Market, Central Market, The Petal Pushers
- **nvidia:nvidia/nemotron-3-ultra-550b-a55b** run 1: Dr. Delphinium, Bachman’s, The Bouqs Co., Bloom & Stem, Flora & Fable, Stems & Stone, J. Morris Flowers, Randy's Flowers, Wildflower, The Dried Florist, Floral & Hardy, Trader Joe’s, Central Market, Whole Foods, Kroger, Tom Thumb, Costco, Sam’s Club, Pressed Floral, The Flower Child, Deep Ellum Florist, North Haven Gardens
- **nvidia:nvidia/nemotron-3-ultra-550b-a55b** run 2: Dr. Delphinium, Bachman’s, The Flower Shop, City Flowers, Floral Studio, Stems & Stone, Bloom & Gather, Petal & Stem, Wildflower, Fleurs de Ville, Lavender & Lace, Central Market Floral, Trader Joe's, Whole Foods, Sprouts, Kroger, Tom Thumb Floral, North Haven Gardens, Ruibal's Plants of Texas, The Plant House
- **nvidia:nvidia/nemotron-3-ultra-550b-a55b** run 3: Bachman's, Dr. Delphinium, Stems & Stone, The Bouqs Co., Flora & Fern, Wildflower, Petal Pushers, Bloom & Gather, Central Market Floral, Kroger, Tom Thumb Floral, Avondale Florist, North Haven Gardens, Floral Studio, Lavender & Lace, The Flower Bar, West Elm, CB2, UrbanStems, Farmgirl Flowers
- **nvidia:nvidia/nemotron-3.5-lightning-30b-a3b** run 1: Bella Fiori, Bloomers Florist, The Flower Shop, Petal + Pooch, The Bouqs Co., UrbanStems
- **nvidia:nvidia/nemotron-3.5-lightning-30b-a3b** run 2: The Flower Truck, Florence's Garden, Petal & Pooch, Urban Stems, The Bouqs Company, Petal Pushers, The Flower Factory
- **nvidia:nvidia/nemotron-3.5-lightning-30b-a3b** run 3: Petal & Epoch, The Bouqs Co., Florentine, The Flower Truck
- **nvidia:minimaxai/minimax-m3.1-flash** run 1: The Flower Box, Lacy's Florist, Madison Floral, Desert Willow Floral, Paper Petal Floral, In Bloom Florals, Moss & Co., Petal & Stem, Bluebonnet Florist, Rose's Floral Shop, White Rock Florist, Inman Floral, Cedar Hill Floral, Rocky Hill Floral, The Arrangement Shop, Blooming Colors, Terry's Flowers, G's Florist
- **nvidia:minimaxai/minimax-m3.1-flash** run 2: Bumgarner Florist, The Dallas Flower Shop, The Flower Cart, Country Brook Florist, Stem + Bloom, In Bloom Florist, Posh Florist, Blooming Rose Florist, The Arrangement Shop, 1-800-Flowers, Teleflora, ProFlowers
- **nvidia:minimaxai/minimax-m3.1-flash** run 3: The Dallas Flower Shop, Carter & Co., The Arrangement Room, Stem, Blossom, In Bloom, Central Market Floral, 1-800-Flowers, Teleflora, FTD
- **nvidia:google/gemma-4-31b-it** run 1: The Flower Shop, Flowers for Friends, Flower Shop of Dallas, The Floral Design Studio, Flowers by Flora, Dallas Farmers Market
- **nvidia:google/gemma-4-31b-it** run 2: ERROR ReadTimeout
- **nvidia:google/gemma-4-31b-it** run 3: The Flower Shop, Flowers for Friends, Flower Child, The Dallas Florist, Flowers by Flora
- **openrouter:perplexity/sonar** run 1: Grey Gardens, Avant Garden, Twelve Thirty Four Boutique, McShan Florist, PRESCH Petals, Lewis Floral + Events, All Occasions Florist, DIRT Flowers, In Bloom Flowers, Mockingbird Florist, Floral Concepts
- **openrouter:perplexity/sonar** run 2: Grey Gardens, Avant Garden, Twelve Thirty Four Boutique, McShan Florist, DIRT Flowers, In Bloom Flowers, Lewis Floral + Events, PRESCH Petals, The Rogue Rose, Floral Concepts, Mockingbird Florist, The Corner Market, My Obsession Floral, Freesia, Joy Cook Designs, BeauMonde Flora, En Fleur
- **openrouter:perplexity/sonar** run 3: Grey Gardens, Avant Garden, McShan Florist, DIRT Flowers, PRESCH Petals, Lewis Floral + Events, In Bloom Flowers, The Corner Market, Floral Concepts, Mockingbird Florist
- **openrouter:openai/gpt-5-mini:online** run 1: Dr Delphinium, McShan Florist, Lane Florist, Twelve Thirty Four, Bottega de Flores, PRESCH Petals, All Occasions Florist, Estrella’s Flower Shop
- **openrouter:openai/gpt-5-mini:online** run 2: ERROR 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry a
- **openrouter:openai/gpt-5-mini:online** run 3: ERROR 402 {"error":{"message":"This request's maximum cost exceeds your available credits. Add credits, or lower max_tokens or
- **openrouter:anthropic/claude-haiku-5.5:online** run 1: McShan Florist, Dr. Delphinium, Avant Garden, Cebolla, DIRT Flowers, Le Bloom, Grey Gardens, The T Shop, Park City Petals
- **openrouter:anthropic/claude-haiku-5.5:online** run 2: Avant Garden, Cebolla, Dr. Delphinium, Billie Ball Co, McShan Florist, In Bloom Flowers on Mockingbird, Lane Florist, Estrella's Flower Shop, Park Cities Petals, Petals & Stems Florist, Lake Highlands Flowers, Mille Fleurs Flowers, Designs East Florist, DIRT, Twelve Thirty Four, The T Shop, PRESCH Petals, Floral Bar
- **openrouter:anthropic/claude-haiku-5.5:online** run 3: Avant Garden, Cebolla, Billie Ball Co, Dr. Delphinium, Twelve Thirty Four, Floral Bar, McShan Florist, DIRT, The T Shop, Lane Florist, In Bloom Flowers on Mockingbird, Estrella's Flower Shop, From You Flowers
- **openrouter:openai/gpt-5-mini** run 1: ERROR 402 {"error":{"message":"This request's maximum cost exceeds your available credits. Add credits, or lower max_tokens or
- **openrouter:openai/gpt-5-mini** run 2: ERROR 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry a
- **openrouter:openai/gpt-5-mini** run 3: ERROR 402 {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 4000 tokens, but c

### same-day flower delivery Dallas

- **gemini:gemini-3.8-flash [memory]** run 1: Dr. Delphinium Designs & Events, Bellarosa Flowers, Park Cities Petals, Floom, Teleflora, From You Flowers
- **gemini:gemini-3.8-flash [memory]** run 2: Dr. Delphinium Designs & Events, Belen Flowers, Avant Garden, Park Cities Petals, Central Market, Instacart, Uber Eats, DoorDash, Whole Foods, Market Street, UrbanStems, Floom
- **gemini:gemini-3.8-flash [memory]** run 3: McShan Florist, Dr Delphinium Designs & Events, Park Cities Petals, Dallas Flower Market, Floom, UrbanStems
- **gemini:gemini-3.8-flash [search]** run 1: Dr Delphinium Designs & Events, DIRT Flowers, McShan Florist, In Bloom Flowers, Flower Boom Dallas, UrbanStems, BloomNation, DoorDash, Uber Eats, Instacart, Central Market, Whole Foods
- **gemini:gemini-3.8-flash [search]** run 2: Dr. Delphinium Designs & Events, McShan Florist, DIRT Flowers, In Bloom Flowers, All Occasions Florist, DoorDash, Uber Eats, Instacart, Central Market Floral, Trader Joe's
- **gemini:gemini-3.8-flash [search]** run 3: Dr. Delphinium Designs & Events, In Bloom Flowers, DIRT Flowers, Dallas House of Flowers, All Occasions Florist, Floom, BloomNation, UrbanStems, Uber Eats, DoorDash, Central Market, Whole Foods, Trader Joe's
- **gemini:gemini-3.8-flash [maps_dallas]** run 1: In Bloom Flowers on Mockingbird, Designs East Florist & Interior, Flower Boulevard, Lovely Flowers Dallas, Dallas Flower Florist
- **gemini:gemini-3.8-flash [maps_dallas]** run 2: Flower Delivery Dallas, In Bloom Flowers on Mockingbird, Lovely Flowers Dallas, Flower Boulevard, All Blooming Flowers
- **gemini:gemini-3.8-flash [maps_dallas]** run 3: Flower Delivery Dallas, Flower Boulevard, In Bloom Flowers on Mockingbird, Lovely Flowers Dallas, All Blooming Flowers
- **nvidia:moonshotai/kimi-k3.1-pro** run 1: McShan Florist, Dr Delphinium, 1-800-Flowers, FTD, Teleflora
- **nvidia:moonshotai/kimi-k3.1-pro** run 2: McShan Florist, Dr Delphinium, Teleflora, 1-800-Flowers
- **nvidia:moonshotai/kimi-k3.1-pro** run 3: McShan Florist, Dr Delphinium Designs & Events, Cebolla Fine Flowers, Teleflora, FTD
- **nvidia:mistralai/mistral-large-4-1t-a52b** run 1: Dempsey's, Bliss Floral Studio, The Petal Pusher, Garden Gate, White Rock Gardens, Central Market, 1-800-Flowers, Teleflora, FTD, UrbanStems, DoorDash, Uber Eats, Grubhub, Instacart, Whole Foods
- **nvidia:mistralai/mistral-large-4-1t-a52b** run 2: Holly Pappas, Blush & Bloom, Texas General Floral, Flower Cart, Central Market Florists, 1-800-Flowers, Teleflora, FTD, Amazon Flowers, The Bouqs, DoorDash, Uber Eats, Grubhub, Instacart, Central Market, Whole Foods
- **nvidia:mistralai/mistral-large-4-1t-a52b** run 3: 1-800-Flowers, Teleflora, FTD, UrbanStems, The Bouqs, DoorDash, Uber Eats, Grubhub, Instacart, Whole Foods Market, Central Market, Amazon, The Flower Bar, Dallas Flower Market
- **nvidia:nvidia/nemotron-3-ultra-550b-a55b** run 1: Bachman's, Dallas Blooms, The Bouqs Co., Flower Child, Nest Floral, Petals & Twigs, Wildflower Florist, Farmgirl Flowers, UrbanStems, 1-800-Flowers, Teleflora, FTD, Fort Worth Florist, Bloom & Grow
- **nvidia:nvidia/nemotron-3-ultra-550b-a55b** run 2: Dr. Delphinium, Bachman's Florist, The Flower Market, Petals & Twigs, City Flowers Dallas, Katherine's Floral Design, North Haven Gardens, Bloomist, Farmgirl Flowers, Bouqs, UrbanStems, 1-800-Flowers, Teleflora, FTD, DoorDash, Uber Eats, Central Market, Whole Foods, Trader Joe's, Kroger, Tom Thumb, Costco, Sam's Club, The Flower Shop FW, Bloom & Grow
- **nvidia:nvidia/nemotron-3-ultra-550b-a55b** run 3: 1-800-Flowers, Teleflora, FTD, Whole Foods, Central Market, Costco, Instacart, DoorDash, Dr. Delphinium, Bachman's Florist, The Flower Shop, Petals & Twigs, Nest Floral, City Flowers Dallas, Kitty's Flowers, Blooms & Co, BloomNation, The Bouqs Co., Uber Eats, Tom Thumb, Kroger, Sprouts, Trader Joe's, H-E-B, Farmgirl Flowers
- **nvidia:nvidia/nemotron-3.5-lightning-30b-a3b** run 1: The Dallas Flower Shop, Petal Pushers Dallas, Bloom & Grow, The Bouqs Co., 1-800-Flowers, ProFlowers, Teleflora, UrbanStems, From You Flowers
- **nvidia:nvidia/nemotron-3.5-lightning-30b-a3b** run 2: 1-800-Flowers, FTD, The Bouqs Company, Petal & Poem, The Flower Truck, Bloom & Grow
- **nvidia:nvidia/nemotron-3.5-lightning-30b-a3b** run 3: The Flower Shop (Dallas), Ba-Ba-Bouquet, Petal & Poem, 1-800-Flowers, ProFlowers, Teleflora
- **nvidia:minimaxai/minimax-m3.1-flash** run 1: FTD (1-800-Flowers.com), Teleflora, The Bouqs, ProFlowers, Bloom & Wild, Farmgirl Flowers, Luna & Grove, Hollybrook Floral Design, Blooming Colors Floral, In Bloom Floral, The Flower Merchant, Kroger, Albertsons, Walmart, Central Market
- **nvidia:minimaxai/minimax-m3.1-flash** run 2: The Bouqs, 1-800-Flowers, FTD (Famous Delivery Today), Teleflora, ProFlowers, Stem & Co., Blooming Wild, Petal & Stem, Noble & Co., The Flower Cart, DoorDash, UberEats, Grubhub, OrderFlowers, eFlorist, Good to Grow, Urban Harvest
- **nvidia:minimaxai/minimax-m3.1-flash** run 3: 1-800-Flowers, FTD (Federated Florists of America), Teleflora, The Bouqs, ProFlowers, Stem & Bower, The Garden Shop, Highland Park Florist, Lee's Florist, In Bloom, Nottington's Florist, Village Flower Shop, Blooming Colors, Instacart, Central Market, Sprouts, Uber Eats, DoorDash, Amazon Same-Day, Whole Foods, Trader Joe's
- **nvidia:google/gemma-4-31b-it** run 1: Dallas Floral Design, The Flower Shop (Dallas), Flowers by Design, DoorDash, UberEats, Grubhub, Whole Foods, Central Market, Instacart, 1-800-Flowers, FTD, Teleflora, The Bouqs Co., BloomNation
- **nvidia:google/gemma-4-31b-it** run 2: Dallas Blooms, The Flower Shop, DoorDash, UberEats, Grubhub, Whole Foods, Central Market, Instacart, H-E-B, Kroger, 1-800-Flowers, FTD, Teleflora, The Bloom That Fits, UrbanStems
- **nvidia:google/gemma-4-31b-it** run 3: Dallas Blooms, The Flower Shop, DoorDash, UberEats, Grubhub, Whole Foods, Central Market, Instacart, H-E-B, Kroger, 1-800-Flowers, FTD, Teleflora, The Bloom Effect, UrbanStems
- **openrouter:perplexity/sonar** run 1: DIRT Flowers, It's Your Florist, Flowers by Coley Dallas, In Bloom Flowers, UrbanStems, Magic World Flowers, Flower Boom Dallas
- **openrouter:perplexity/sonar** run 2: DIRT Flowers, It’s Your Florist, Flowers by Coley Dallas, Dallas House of Flowers, Flower Boom Dallas, FloraLux TX, In Bloom Flowers, UrbanStems, Floom, Bloom Central, 1st in Flowers, From You Flowers, Teleflora
- **openrouter:perplexity/sonar** run 3: DIRT Flowers, It’s Your Florist, Flowers by Coley Dallas, Dallas House of Flowers, The Palace of Flowers, FloraLux TX, Flower Boom Dallas, In Bloom Flowers, Magic World Flowers, The Bouqs Co., From You Flowers, Teleflora, ProFlowers, FTD, Estrella’s Flower Shop, Floom, Bloom Central, 1st in Flowers
- **openrouter:openai/gpt-5-mini:online** run 1: ERROR 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry a
- **openrouter:openai/gpt-5-mini:online** run 2: ERROR 402 {"error":{"message":"This request's maximum cost exceeds your available credits. Add credits, or lower max_tokens or
- **openrouter:openai/gpt-5-mini:online** run 3: ERROR 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry a
- **openrouter:anthropic/claude-haiku-5.5:online** run 1: McShan Florist, Dallas Florist (Dallas Flora), Flower Delivery Dallas, Floom, The Bouqs Co., In Bloom Flowers, Dr Delphinium, All Occasions Florist (Oak Lawn), Dallas House of Flowers
- **openrouter:anthropic/claude-haiku-5.5:online** run 2: Bouqs, McShan Florist, Dallas House of Flowers, Flower Delivery Dallas, Floom, Dallas Flora (Dallas Florist), In Bloom Flowers, Dr Delphinium, All Occasions Florist (Oak Lawn)
- **openrouter:anthropic/claude-haiku-5.5:online** run 3: ERROR 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry a
- **openrouter:openai/gpt-5-mini** run 1: ERROR 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry a
- **openrouter:openai/gpt-5-mini** run 2: ERROR 402 {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 4000 tokens, but c
- **openrouter:openai/gpt-5-mini** run 3: ERROR 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry a

### best florist near me

- **gemini:gemini-3.8-flash [memory]** run 1: Floom, UrbanStems, The Bouqs Co.
- **gemini:gemini-3.8-flash [memory]** run 2: (no businesses named)
- **gemini:gemini-3.8-flash [memory]** run 3: (no businesses named)
- **gemini:gemini-3.8-flash [search]** run 1: Blinkit, Zepto, Swiggy Instamart, Interflora India, Ferns N Petals (FNP), FlowerAura, IGP (Indian Gifts Portal)
- **gemini:gemini-3.8-flash [search]** run 2: Blinkit, Zepto, Swiggy Instamart, Ferns N Petals (FNP), FlowerAura, Interflora India, MyFlowerTree, Winni
- **gemini:gemini-3.8-flash [search]** run 3: Blinkit, Zepto, Swiggy Instamart, Interflora India, Ferns N Petals (FNP), FlowerAura
- **gemini:gemini-3.8-flash [maps_dallas]** run 1: Flower Boulevard, PRESCH Petals, Designs East Florist & Interior, All Blooming Flowers, Lovely Flowers Dallas
- **gemini:gemini-3.8-flash [maps_dallas]** run 2: PRESCH Petals, Flower Boulevard, DLux Roses - Eternity Roses, All Blooming Flowers, Lovely Flowers Dallas
- **gemini:gemini-3.8-flash [maps_dallas]** run 3: PRESCH Petals, Flower Boulevard, Designs East Florist & Interior, All Blooming Flowers, Lovely Flowers Dallas
- **nvidia:moonshotai/kimi-k3.1-pro** run 1: (no businesses named)
- **nvidia:moonshotai/kimi-k3.1-pro** run 2: (no businesses named)
- **nvidia:moonshotai/kimi-k3.1-pro** run 3: (no businesses named)
- **nvidia:mistralai/mistral-large-4-1t-a52b** run 1: Whole Foods, Trader Joe's, 1-800-Flowers, Teleflora
- **nvidia:mistralai/mistral-large-4-1t-a52b** run 2: (no businesses named)
- **nvidia:mistralai/mistral-large-4-1t-a52b** run 3: (no businesses named)
- **nvidia:nvidia/nemotron-3-ultra-550b-a55b** run 1: BloomNation, FlowerShopNetwork, LocalFlorist.com, Farmgirl Flowers, UrbanStems, The Bouqs Co.
- **nvidia:nvidia/nemotron-3-ultra-550b-a55b** run 2: (no businesses named)
- **nvidia:nvidia/nemotron-3-ultra-550b-a55b** run 3: Whole Foods, Trader Joe's
- **nvidia:nvidia/nemotron-3.5-lightning-30b-a3b** run 1: (no businesses named)
- **nvidia:nvidia/nemotron-3.5-lightning-30b-a3b** run 2: (no businesses named)
- **nvidia:nvidia/nemotron-3.5-lightning-30b-a3b** run 3: (no businesses named)
- **nvidia:minimaxai/minimax-m3.1-flash** run 1: (no businesses named)
- **nvidia:minimaxai/minimax-m3.1-flash** run 2: (no businesses named)
- **nvidia:minimaxai/minimax-m3.1-flash** run 3: 1-800-Flowers, FTD, Teleflora, The Bouqs, ProFlowers
- **nvidia:google/gemma-4-31b-it** run 1: ERROR ReadTimeout
- **nvidia:google/gemma-4-31b-it** run 2: (no businesses named)
- **nvidia:google/gemma-4-31b-it** run 3: (no businesses named)
- **openrouter:perplexity/sonar** run 1: (no businesses named)
- **openrouter:perplexity/sonar** run 2: Allen’s Flowers & Plants, Barliz Flowers, FLEURT, Confucius Florist, Isabel Florist
- **openrouter:perplexity/sonar** run 3: (no businesses named)
- **openrouter:openai/gpt-5-mini:online** run 1: ERROR 402 {"error":{"message":"This request's maximum cost exceeds your available credits. Add credits, or lower max_tokens or
- **openrouter:openai/gpt-5-mini:online** run 2: ERROR 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry a
- **openrouter:openai/gpt-5-mini:online** run 3: ERROR 402 {"error":{"message":"This request's maximum cost exceeds your available credits. Add credits, or lower max_tokens or
- **openrouter:anthropic/claude-haiku-5.5:online** run 1: ERROR 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry a
- **openrouter:anthropic/claude-haiku-5.5:online** run 2: ERROR 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry a
- **openrouter:anthropic/claude-haiku-5.5:online** run 3: ERROR 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry a
- **openrouter:openai/gpt-5-mini** run 1: ERROR 402 {"error":{"message":"This request's maximum cost exceeds your available credits. Add credits, or lower max_tokens or
- **openrouter:openai/gpt-5-mini** run 2: ERROR 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry a
- **openrouter:openai/gpt-5-mini** run 3: ERROR 402 {"error":{"message":"This request's maximum cost exceeds your available credits. Add credits, or lower max_tokens or

## Errors

- nvidia:moonshotai/kimi-k3.1-pro | best florists in Dallas | run 3: ReadTimeout
- nvidia:mistralai/mistral-large-4-1t-a52b | best florists in Dallas | run 1: ReadTimeout
- nvidia:mistralai/mistral-large-4-1t-a52b | best florists in Dallas | run 2: ReadTimeout
- nvidia:google/gemma-4-31b-it | best florists in Dallas | run 2: ReadTimeout
- nvidia:google/gemma-4-31b-it | best florist near me | run 1: ReadTimeout
- openrouter:openai/gpt-5-mini:online | best florists in Dallas | run 2: 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add credits.","code":402,"metadata":{"reason"
- openrouter:openai/gpt-5-mini:online | best florists in Dallas | run 3: 402 {"error":{"message":"This request's maximum cost exceeds your available credits. Add credits, or lower max_tokens or prompt size.","code":402,"metadata":{"reason":"weight_exceeds_budget","limit_so
- openrouter:openai/gpt-5-mini:online | same-day flower delivery Dallas | run 1: 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add credits.","code":402,"metadata":{"reason"
- openrouter:openai/gpt-5-mini:online | same-day flower delivery Dallas | run 2: 402 {"error":{"message":"This request's maximum cost exceeds your available credits. Add credits, or lower max_tokens or prompt size.","code":402,"metadata":{"reason":"weight_exceeds_budget","limit_so
- openrouter:openai/gpt-5-mini:online | same-day flower delivery Dallas | run 3: 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add credits.","code":402,"metadata":{"reason"
- openrouter:openai/gpt-5-mini:online | best florist near me | run 1: 402 {"error":{"message":"This request's maximum cost exceeds your available credits. Add credits, or lower max_tokens or prompt size.","code":402,"metadata":{"reason":"weight_exceeds_budget","limit_so
- openrouter:openai/gpt-5-mini:online | best florist near me | run 2: 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add credits.","code":402,"metadata":{"reason"
- openrouter:openai/gpt-5-mini:online | best florist near me | run 3: 402 {"error":{"message":"This request's maximum cost exceeds your available credits. Add credits, or lower max_tokens or prompt size.","code":402,"metadata":{"reason":"weight_exceeds_budget","limit_so
- openrouter:anthropic/claude-haiku-5.5:online | same-day flower delivery Dallas | run 3: 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add credits.","code":402,"metadata":{"reason"
- openrouter:anthropic/claude-haiku-5.5:online | best florist near me | run 1: 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add credits.","code":402,"metadata":{"reason"
- openrouter:anthropic/claude-haiku-5.5:online | best florist near me | run 2: 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add credits.","code":402,"metadata":{"reason"
- openrouter:anthropic/claude-haiku-5.5:online | best florist near me | run 3: 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add credits.","code":402,"metadata":{"reason"
- openrouter:openai/gpt-5-mini | best florists in Dallas | run 1: 402 {"error":{"message":"This request's maximum cost exceeds your available credits. Add credits, or lower max_tokens or prompt size.","code":402,"metadata":{"reason":"weight_exceeds_budget","limit_so
- openrouter:openai/gpt-5-mini | best florists in Dallas | run 2: 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add credits.","code":402,"metadata":{"reason"
- openrouter:openai/gpt-5-mini | best florists in Dallas | run 3: 402 {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 4000 tokens, but can only afford 2971. To increase, visit https://openrouter.ai/workspaces/default
- openrouter:openai/gpt-5-mini | same-day flower delivery Dallas | run 1: 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add credits.","code":402,"metadata":{"reason"
- openrouter:openai/gpt-5-mini | same-day flower delivery Dallas | run 2: 402 {"error":{"message":"This request requires more credits, or fewer max_tokens. You requested up to 4000 tokens, but can only afford 2971. To increase, visit https://openrouter.ai/workspaces/default
- openrouter:openai/gpt-5-mini | same-day flower delivery Dallas | run 3: 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add credits.","code":402,"metadata":{"reason"
- openrouter:openai/gpt-5-mini | best florist near me | run 1: 402 {"error":{"message":"This request's maximum cost exceeds your available credits. Add credits, or lower max_tokens or prompt size.","code":402,"metadata":{"reason":"weight_exceeds_budget","limit_so
- openrouter:openai/gpt-5-mini | best florist near me | run 2: 402 {"error":{"message":"This request would exceed your available credits given your current in-flight requests. Retry after in-flight requests settle, or add credits.","code":402,"metadata":{"reason"
- openrouter:openai/gpt-5-mini | best florist near me | run 3: 402 {"error":{"message":"This request's maximum cost exceeds your available credits. Add credits, or lower max_tokens or prompt size.","code":402,"metadata":{"reason":"weight_exceeds_budget","limit_so