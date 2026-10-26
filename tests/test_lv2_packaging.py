import os,subprocess,sys,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools'))
from package_lv2 import source_commit
class BuildMetadata(unittest.TestCase):
 def test_exported_ci_sources_use_verified_environment_sha(self):
  sha='1234567890abcdef1234567890abcdef12345678'
  with patch('package_lv2.subprocess.check_output',side_effect=subprocess.CalledProcessError(128,['git'])),patch.dict(os.environ,{'GITHUB_SHA':sha}):self.assertEqual(source_commit(),sha)
 def test_missing_git_and_invalid_sha_cannot_produce_package(self):
  with patch('package_lv2.subprocess.check_output',side_effect=FileNotFoundError),patch.dict(os.environ,{'GITHUB_SHA':'not-a-source-commit'}),self.assertRaises(ValueError):source_commit()
 def test_actual_checkout_takes_precedence(self):
  sha='a'*40
  with patch('package_lv2.subprocess.check_output',return_value=sha+'\n'),patch.dict(os.environ,{'GITHUB_SHA':'b'*40}):self.assertEqual(source_commit(),sha)
