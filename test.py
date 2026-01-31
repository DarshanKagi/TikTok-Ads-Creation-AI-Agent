"""
Unit tests for TikTok Ads AI Agent.

Tests cover:
- Pydantic validation (business rules)
- Music logic scenarios
- Mock API behavior
- Error interpretation

Run with: pytest test.py -v
"""

import pytest
from agent import AdConfig
from mock_api import MockTikTokAPI, ErrorInterpreter


# ============================================================================
# VALIDATION TESTS
# ============================================================================

class TestAdConfigValidation:
    """Test Pydantic validation and business rules."""
    
    def test_valid_traffic_campaign_no_music(self):
        """Traffic campaign allows no music."""
        config = AdConfig(
            campaign_name="Summer Sale 2026",
            objective="Traffic",
            ad_text="Get 50% off on all products! Limited time.",
            cta="Shop Now",
            music_id=None
        )
        assert config.objective == "Traffic"
        assert config.music_id is None
    
    def test_valid_traffic_campaign_with_music(self):
        """Traffic campaign allows music."""
        config = AdConfig(
            campaign_name="Summer Sale 2026",
            objective="Traffic",
            ad_text="Get 50% off on all products!",
            cta="Shop Now",
            music_id="12345"
        )
        assert config.objective == "Traffic"
        assert config.music_id == "12345"
    
    def test_valid_conversions_campaign_with_music(self):
        """Conversions campaign with music is valid."""
        config = AdConfig(
            campaign_name="Lead Generation",
            objective="Conversions",
            ad_text="Sign up today and get exclusive access!",
            cta="Register Now",
            music_id="67890"
        )
        assert config.objective == "Conversions"
        assert config.music_id == "67890"
    
    def test_conversions_requires_music(self):
        """Conversions campaign MUST have music."""
        with pytest.raises(ValueError, match="Music is REQUIRED"):
            AdConfig(
                campaign_name="Lead Gen Campaign",
                objective="Conversions",
                ad_text="Sign up for our newsletter!",
                cta="Subscribe",
                music_id=None  # This should fail
            )
    
    def test_campaign_name_min_length(self):
        """Campaign name must be at least 3 characters."""
        with pytest.raises(ValueError, match="at least 3 characters"):
            AdConfig(
                campaign_name="AB",  # Too short
                objective="Traffic",
                ad_text="Test ad",
                cta="Click"
            )
    
    def test_campaign_name_trimming(self):
        """Campaign name should be trimmed."""
        config = AdConfig(
            campaign_name="  Test  ",
            objective="Traffic",
            ad_text="Test ad text",
            cta="Click"
        )
        assert config.campaign_name == "Test"
    
    def test_ad_text_max_length(self):
        """Ad text cannot exceed 100 characters."""
        with pytest.raises(ValueError, match="cannot exceed 100 characters"):
            AdConfig(
                campaign_name="Test Campaign",
                objective="Traffic",
                ad_text="A" * 101,  # 101 characters - too long
                cta="Click"
            )
    
    def test_ad_text_exactly_100_chars(self):
        """Ad text with exactly 100 characters is valid."""
        config = AdConfig(
            campaign_name="Test",
            objective="Traffic",
            ad_text="A" * 100,  # Exactly 100 chars
            cta="Click"
        )
        assert len(config.ad_text) == 100
    
    def test_invalid_objective(self):
        """Objective must be Traffic or Conversions."""
        with pytest.raises(ValueError, match="must be 'Traffic' or 'Conversions'"):
            AdConfig(
                campaign_name="Test",
                objective="InvalidObjective",
                ad_text="Test",
                cta="Click"
            )
    
    def test_empty_music_id_rejected(self):
        """Empty music ID should be rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            AdConfig(
                campaign_name="Test",
                objective="Traffic",
                ad_text="Test",
                cta="Click",
                music_id="   "  # Empty after trim
            )


# ============================================================================
# MOCK API TESTS
# ============================================================================

class TestMockTikTokAPI:
    """Test Mock API behavior."""
    
    def setup_method(self):
        """Setup for each test."""
        self.api = MockTikTokAPI(simulate_failures=False)
    
    def test_validate_valid_music_id(self):
        """Valid music ID returns success."""
        result = self.api.validate_music_id("12345", "token")
        
        assert result["success"] is True
        assert result["data"]["music_id"] == "12345"
        assert "title" in result["data"]
        assert "artist" in result["data"]
    
    def test_validate_invalid_music_id(self):
        """Invalid music ID returns error."""
        result = self.api.validate_music_id("99999", "token")
        
        assert result["success"] is False
        assert result["error_code"] == "MUSIC_NOT_FOUND"
        assert "99999" in result["message"]
    
    def test_upload_music(self):
        """Music upload returns new ID."""
        result = self.api.upload_music("/path/to/track.mp3", "token")
        
        assert result["success"] is True
        assert result["data"]["music_id"].startswith("UPLOAD_")
        assert result["data"]["status"] == "ready"
        
        # Uploaded music should be in valid IDs
        uploaded_id = result["data"]["music_id"]
        assert uploaded_id in self.api.valid_music_ids
    
    def test_create_ad_success(self):
        """Successful ad creation."""
        payload = {
            "campaign_name": "Test",
            "objective": "Traffic",
            "ad_text": "Test ad",
            "cta": "Click"
        }
        
        result = self.api.create_ad(payload, "token")
        
        assert result["success"] is True
        assert "ad_id" in result["data"]
        assert "campaign_id" in result["data"]
        assert result["data"]["status"] == "pending_review"
    
    def test_mock_api_with_failures_enabled(self):
        """Test that failure simulation works."""
        api_with_failures = MockTikTokAPI(simulate_failures=True, failure_rate=1.0)
        
        # With 100% failure rate, should get error
        result = api_with_failures.validate_music_id("12345", "token")
        
        # Should be an error (either token error or other)
        assert result["success"] is False
        assert "error_code" in result


# ============================================================================
# ERROR INTERPRETER TESTS
# ============================================================================

class TestErrorInterpreter:
    """Test error interpretation."""
    
    def test_invalid_token_error(self):
        """Invalid token error interpretation."""
        error = ErrorInterpreter.interpret("INVALID_TOKEN")
        
        assert "token" in error["explanation"].lower()
        assert "refresh" in error["action"].lower()
        assert error["retryable"] is True
    
    def test_insufficient_permissions_error(self):
        """Insufficient permissions error interpretation."""
        error = ErrorInterpreter.interpret("INSUFFICIENT_PERMISSIONS")
        
        assert "permission" in error["explanation"].lower()
        assert "Developer Portal" in error["action"]
        assert error["retryable"] is False
    
    def test_music_not_found_error(self):
        """Music not found error interpretation."""
        error = ErrorInterpreter.interpret("MUSIC_NOT_FOUND")
        
        assert "music" in error["explanation"].lower()
        assert error["retryable"] is False
        assert error["severity"] == "low"
    
    def test_geo_restricted_error(self):
        """Geo-restriction error interpretation."""
        error = ErrorInterpreter.interpret("GEO_RESTRICTED")
        
        assert "region" in error["explanation"].lower()
        assert error["retryable"] is False
        assert error["severity"] == "high"
    
    def test_unknown_error_code(self):
        """Unknown error code gets default message."""
        error = ErrorInterpreter.interpret("UNKNOWN_ERROR_12345")
        
        assert "unexpected" in error["explanation"].lower()
        assert error["retryable"] is True


# ============================================================================
# INTEGRATION TESTS
# ============================================================================

class TestMusicLogicIntegration:
    """Test complete music logic workflows."""
    
    def setup_method(self):
        """Setup for each test."""
        self.api = MockTikTokAPI(simulate_failures=False)
    
    def test_traffic_no_music_workflow(self):
        """Complete workflow: Traffic campaign without music."""
        # Step 1: Create config without music
        config = AdConfig(
            campaign_name="Traffic Test",
            objective="Traffic",
            ad_text="Check out our new products!",
            cta="Learn More",
            music_id=None
        )
        
        # Step 2: Submit to API
        result = self.api.create_ad(config.dict(), "token")
        
        # Should succeed
        assert result["success"] is True
        assert "ad_id" in result["data"]
    
    def test_conversions_with_valid_music_workflow(self):
        """Complete workflow: Conversions with valid music."""
        # Step 1: Create config with music
        config = AdConfig(
            campaign_name="Conversion Test",
            objective="Conversions",
            ad_text="Sign up now for exclusive benefits!",
            cta="Register",
            music_id="12345"
        )
        
        # Step 2: Validate music
        music_result = self.api.validate_music_id("12345", "token")
        assert music_result["success"] is True
        
        # Step 3: Submit ad
        ad_result = self.api.create_ad(config.dict(), "token")
        assert ad_result["success"] is True
    
    def test_upload_music_workflow(self):
        """Complete workflow: Upload custom music."""
        # Step 1: Upload music
        upload_result = self.api.upload_music("/path/to/custom.mp3", "token")
        assert upload_result["success"] is True
        
        new_music_id = upload_result["data"]["music_id"]
        
        # Step 2: Create config with uploaded music
        config = AdConfig(
            campaign_name="Custom Music Test",
            objective="Conversions",
            ad_text="Experience our latest collection!",
            cta="Shop Now",
            music_id=new_music_id
        )
        
        # Step 3: Validate uploaded music
        validate_result = self.api.validate_music_id(new_music_id, "token")
        assert validate_result["success"] is True
        
        # Step 4: Submit ad
        ad_result = self.api.create_ad(config.dict(), "token")
        assert ad_result["success"] is True


# ============================================================================
# RUN TESTS
# ============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("🧪 Running TikTok Ads AI Agent Tests")
    print("=" * 60)
    
    # Run pytest
    pytest.main([
        __file__,
        "-v",  # Verbose
        "--tb=short",  # Short traceback
        "--color=yes"  # Colored output
    ])
