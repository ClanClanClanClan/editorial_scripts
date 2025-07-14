#!/usr/bin/env python3
"""
Code validation script to verify stealth integration is complete
Analyzes the SIAM scraper code without running it
"""

import re
from pathlib import Path

def analyze_stealth_integration():
    """Analyze the stealth integration in SIAM scraper"""
    print("🔍 ANALYZING STEALTH INTEGRATION")
    print("=" * 60)
    
    siam_scraper_path = Path("src/infrastructure/scrapers/siam_scraper.py")
    stealth_manager_path = Path("src/infrastructure/scrapers/stealth_manager.py")
    
    if not siam_scraper_path.exists():
        print("❌ SIAM scraper file not found")
        return False
    
    if not stealth_manager_path.exists():
        print("❌ Stealth manager file not found")
        return False
    
    # Read files
    with open(siam_scraper_path) as f:
        siam_content = f.read()
    
    with open(stealth_manager_path) as f:
        stealth_content = f.read()
    
    # Analysis results
    analysis = {}
    
    # 1. Check stealth manager import
    print("\n🔍 Checking Stealth Manager Import...")
    if "from src.infrastructure.scrapers.stealth_manager import StealthManager" in siam_content:
        print("✅ StealthManager is imported")
        analysis['stealth_import'] = True
    else:
        print("❌ StealthManager import missing")
        analysis['stealth_import'] = False
    
    # 2. Check stealth manager initialization
    print("\n🔍 Checking Stealth Manager Initialization...")
    if "self.stealth_manager = StealthManager(" in siam_content:
        print("✅ StealthManager is initialized")
        analysis['stealth_init'] = True
    else:
        print("❌ StealthManager initialization missing")
        analysis['stealth_init'] = False
    
    # 3. Check human-like typing usage
    print("\n🔍 Checking Human-like Typing Integration...")
    human_typing_count = len(re.findall(r'human_like_typing', siam_content))
    if human_typing_count > 0:
        print(f"✅ human_like_typing used {human_typing_count} times")
        analysis['human_typing'] = True
    else:
        print("❌ human_like_typing not used")
        analysis['human_typing'] = False
    
    # 4. Check human-like clicking usage
    print("\n🔍 Checking Human-like Clicking Integration...")
    human_click_count = len(re.findall(r'human_like_click', siam_content))
    if human_click_count > 0:
        print(f"✅ human_like_click used {human_click_count} times")
        analysis['human_click'] = True
    else:
        print("❌ human_like_click not used")
        analysis['human_click'] = False
    
    # 5. Check human-like delays
    print("\n🔍 Checking Human-like Delay Integration...")
    human_delay_count = len(re.findall(r'human_like_delay', siam_content))
    if human_delay_count > 0:
        print(f"✅ human_like_delay used {human_delay_count} times")
        analysis['human_delay'] = True
    else:
        print("❌ human_like_delay not used")
        analysis['human_delay'] = False
    
    # 6. Check bot detection
    print("\n🔍 Checking Bot Detection Integration...")
    if "detect_captcha_or_challenge" in siam_content:
        print("✅ Bot detection is integrated")
        analysis['bot_detection'] = True
    else:
        print("❌ Bot detection not integrated")
        analysis['bot_detection'] = False
    
    # 7. Check stealth context setup
    print("\n🔍 Checking Stealth Context Setup...")
    if "get_context_options" in siam_content:
        print("✅ Stealth context options are used")
        analysis['context_stealth'] = True
    else:
        print("❌ Stealth context options not used")
        analysis['context_stealth'] = False
    
    # 8. Check page stability waiting
    print("\n🔍 Checking Page Stability Integration...")
    if "wait_for_page_stability" in siam_content:
        print("✅ Page stability waiting is integrated")
        analysis['page_stability'] = True
    else:
        print("❌ Page stability waiting not integrated")
        analysis['page_stability'] = False
    
    # 9. Check stealth manager features
    print("\n🔍 Analyzing Stealth Manager Features...")
    stealth_features = {
        'user_agent_rotation': 'USER_AGENTS' in stealth_content,
        'viewport_randomization': 'VIEWPORTS' in stealth_content,
        'request_blocking': 'blocked_domains' in stealth_content,
        'webdriver_stealth': 'inject_stealth_scripts' in stealth_content,
        'mouse_movement': 'random_mouse_movement' in stealth_content,
        'human_scrolling': 'scroll_like_human' in stealth_content
    }
    
    for feature, present in stealth_features.items():
        status = "✅" if present else "❌"
        print(f"   {status} {feature}")
        analysis[feature] = present
    
    # 10. Check authentication flow integration
    print("\n🔍 Checking Authentication Flow Integration...")
    auth_patterns = [
        r'_enter_orcid_credentials.*human_like_typing',
        r'human_like_click.*submit',
        r'wait_for_page_stability.*page'
    ]
    
    auth_integration_score = 0
    for pattern in auth_patterns:
        if re.search(pattern, siam_content, re.DOTALL):
            auth_integration_score += 1
    
    if auth_integration_score >= 2:
        print(f"✅ Authentication flow properly integrated ({auth_integration_score}/3 patterns)")
        analysis['auth_integration'] = True
    else:
        print(f"❌ Authentication flow needs improvement ({auth_integration_score}/3 patterns)")
        analysis['auth_integration'] = False
    
    # Calculate overall score
    total_checks = len(analysis)
    passed_checks = sum(analysis.values())
    score = passed_checks / total_checks * 100
    
    print(f"\n{'=' * 60}")
    print("🎯 STEALTH INTEGRATION ANALYSIS SUMMARY")
    print(f"{'=' * 60}")
    print(f"Integration Score: {score:.1f}% ({passed_checks}/{total_checks})")
    
    print(f"\n📊 Feature Analysis:")
    for feature, status in analysis.items():
        symbol = "✅" if status else "❌"
        print(f"   {symbol} {feature.replace('_', ' ').title()}")
    
    if score >= 80:
        print(f"\n🎉 EXCELLENT INTEGRATION!")
        print("The stealth integration is comprehensive and production-ready.")
    elif score >= 60:
        print(f"\n✅ GOOD INTEGRATION")
        print("Most stealth features are integrated. Minor improvements possible.")
    else:
        print(f"\n⚠️ NEEDS IMPROVEMENT")
        print("Stealth integration requires more work before production use.")
    
    # Recommendations
    print(f"\n📋 Recommendations:")
    if not analysis.get('human_typing', False):
        print("   - Integrate human_like_typing for credential input")
    if not analysis.get('bot_detection', False):
        print("   - Add bot detection and challenge handling")
    if not analysis.get('page_stability', False):
        print("   - Use wait_for_page_stability for reliable page loading")
    if score == 100:
        print("   - Integration is complete! Ready for testing with real credentials.")
    
    return score >= 80

if __name__ == "__main__":
    try:
        success = analyze_stealth_integration()
        exit(0 if success else 1)
    except Exception as e:
        print(f"❌ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        exit(1)