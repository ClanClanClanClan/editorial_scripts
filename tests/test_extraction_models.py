"""Test extraction models can parse actual legacy JSON."""

import json
from pathlib import Path
from src.ecc.models.extraction_models import (
    ExtractedManuscript,
    Referee,
    Author,
    Documents,
    RefereeReport,
    RefereeTimeline,
    RefereeStatusDetails
)


def test_parse_real_json():
    """Test parsing real JSON from legacy extractor."""
    # Load real JSON file
    json_file = Path("ULTRATHINK_MOR_COMPLETE_20250819_113802.json")
    
    if not json_file.exists():
        print(f"⚠️ Test file {json_file} not found, using minimal test data")
        test_data = {
            "manuscripts": [{
                "id": "TEST-001",
                "category": "Test Category",
                "referees": [{
                    "name": "Test Referee",
                    "email": "test@example.com",
                    "status": "Agreed"
                }]
            }]
        }
    else:
        with open(json_file, 'r') as f:
            test_data = json.load(f)
    
    # Parse manuscripts
    manuscripts = []
    for ms_data in test_data.get('manuscripts', []):
        manuscript = ExtractedManuscript.from_dict(ms_data)
        manuscripts.append(manuscript)
        
        # Verify parsing worked
        assert manuscript.id != ""
        print(f"✅ Parsed manuscript: {manuscript.id}")
        
        # Check referees
        if manuscript.referees:
            print(f"   Referees: {len(manuscript.referees)}")
            for referee in manuscript.referees[:3]:  # Show first 3
                print(f"     - {referee.name} ({referee.status})")
        
        # Check authors
        if manuscript.authors:
            print(f"   Authors: {len(manuscript.authors)}")
            for author in manuscript.authors[:3]:  # Show first 3
                print(f"     - {author.name}")
    
    print(f"\n✅ Successfully parsed {len(manuscripts)} manuscripts")
    return manuscripts


def test_round_trip():
    """Test converting to dict and back."""
    # Create a manuscript
    manuscript = ExtractedManuscript(
        id="TEST-001",
        title="Test Manuscript",
        category="Under Review"
    )
    
    # Add a referee
    referee = Referee(
        name="John Smith",
        email="john@example.com",
        affiliation="Test University",
        status="Agreed"
    )
    manuscript.referees.append(referee)
    
    # Add an author
    author = Author(
        name="Jane Doe",
        email="jane@example.com",
        affiliation="Another University"
    )
    manuscript.authors.append(author)
    
    # Convert to dict
    ms_dict = manuscript.to_dict()
    
    # Parse back
    manuscript2 = ExtractedManuscript.from_dict(ms_dict)
    
    # Verify
    assert manuscript2.id == manuscript.id
    assert manuscript2.title == manuscript.title
    assert len(manuscript2.referees) == 1
    assert manuscript2.referees[0].name == "John Smith"
    assert len(manuscript2.authors) == 1
    assert manuscript2.authors[0].name == "Jane Doe"
    
    print("✅ Round-trip conversion successful")


def test_referee_timeline():
    """Test referee timeline parsing."""
    timeline_data = {
        "invitation_sent": "02-Aug-2025",
        "agreed_to_review": "06-Aug-2025",
        "days_to_respond": 4
    }
    
    timeline = RefereeTimeline.from_dict(timeline_data)
    assert timeline.invitation_sent == "02-Aug-2025"
    assert timeline.agreed_to_review == "06-Aug-2025"
    assert timeline.days_to_respond == 4
    
    print("✅ Timeline parsing successful")


def test_referee_status_details():
    """Test referee status details parsing."""
    status_data = {
        "status": "Agreed",
        "review_received": False,
        "review_pending": True,
        "agreed_to_review": True,
        "declined": False
    }
    
    status = RefereeStatusDetails.from_dict(status_data)
    assert status.status == "Agreed"
    assert status.review_pending == True
    assert status.agreed_to_review == True
    assert status.declined == False
    
    print("✅ Status details parsing successful")


if __name__ == "__main__":
    print("Testing extraction models...")
    print("=" * 60)
    
    # Run tests
    test_parse_real_json()
    test_round_trip()
    test_referee_timeline()
    test_referee_status_details()
    
    print("\n✅ All model tests passed!")