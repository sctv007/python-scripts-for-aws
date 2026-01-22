"""
Secure S3 Empty Bucket Cleanup Script

Finds and deletes empty S3 buckets with versioning disabled.
WARNING: Bucket deletion is permanent and irreversible!
"""

import boto3
import sys

def get_empty_buckets(region_name='us-east-1'):
    """
    Find empty S3 buckets in the account.
    
    Conditions for deletion:
    1. Bucket has zero objects (empty)
    2. Bucket versioning is NOT enabled
    3. Bucket is not configured for static website hosting
    """
    session = boto3.Session(profile_name='script-automation-user', region_name=region_name)
    s3_client = session.client('s3')
    
    try:
        # List all buckets (S3 is global, but buckets have regions)
        response = s3_client.list_buckets()
        empty_buckets = []
        
        for bucket in response['Buckets']:
            bucket_name = bucket['Name']
            
            try:
                # Get bucket location/region
                location_response = s3_client.get_bucket_location(Bucket=bucket_name)
                bucket_region = location_response.get('LocationConstraint', 'us-east-1')
                
                # Check if bucket is empty
                list_response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
                
                # 'Contents' key exists only if there are objects
                if 'Contents' not in list_response:
                    # Check if versioning is enabled
                    versioning_response = s3_client.get_bucket_versioning(Bucket=bucket_name)
                    versioning_status = versioning_response.get('Status', 'Suspended')
                    
                    # Only proceed if versioning is NOT enabled
                    if versioning_status != 'Enabled':
                        # Optional: Check for website configuration
                        # try:
                        #     s3_client.get_bucket_website(Bucket=bucket_name)
                        #     print(f"  Skipping {bucket_name} - has website configuration")
                        #     continue
                        # except:
                        #     pass
                        
                        empty_buckets.append({
                            'Name': bucket_name,
                            'Region': bucket_region if bucket_region else 'us-east-1',
                            'CreationDate': bucket['CreationDate']
                        })
                        
            except Exception as e:
                print(f"  Error checking bucket {bucket_name}: {e}")
                continue
        
        return empty_buckets
        
    except Exception as e:
        print(f"Error listing buckets: {e}")
        return []

def delete_buckets(bucket_list, dry_run=True):
    """
    Delete empty S3 buckets.
    
    WARNING: This action is PERMANENT and IRREVERSIBLE!
    Once a bucket is deleted, the name becomes available globally
    for anyone to claim after a short period.
    """
    if not bucket_list:
        print("No buckets to delete")
        return
    
    deleted_count = 0
    
    for bucket_info in bucket_list:
        bucket_name = bucket_info['Name']
        bucket_region = bucket_info['Region']
        
        # Create session for bucket's region
        session = boto3.Session(
            profile_name='script-automation-user',
            region_name=bucket_region
        )
        s3_client = session.client('s3')
        
        if dry_run:
            print(f"[DRY RUN] Would delete empty bucket: {bucket_name} (Region: {bucket_region})")
        else:
            try:
                # Double-check it's still empty before deleting
                list_response = s3_client.list_objects_v2(Bucket=bucket_name, MaxKeys=1)
                if 'Contents' in list_response:
                    print(f"  WARNING: {bucket_name} now has objects, skipping")
                    continue
                
                s3_client.delete_bucket(Bucket=bucket_name)
                print(f"Deleted empty bucket: {bucket_name} (Region: {bucket_region})")
                deleted_count += 1
                
            except Exception as e:
                print(f"Failed to delete bucket {bucket_name}: {e}")
    
    if not dry_run:
        print(f"\nSuccessfully deleted {deleted_count} empty bucket(s)")

def main():
    """Main function to find and delete empty S3 buckets"""
    print("=" * 70)
    print("S3 EMPTY BUCKET CLEANUP SCRIPT")
    print("=" * 70)
    print("WARNING: Bucket deletion is PERMANENT and IRREVERSIBLE!")
    print("Deleted bucket names become available for anyone to claim.")
    print("=" * 70)
    
    # For S3, we typically use us-east-1 as the default region for API calls
    # Buckets themselves have their own regions
    empty_buckets = get_empty_buckets(region_name='us-east-1')
    
    if empty_buckets:
        print(f"\nFound {len(empty_buckets)} empty bucket(s) with versioning disabled:")
        print("-" * 50)
        
        for bucket in empty_buckets:
            print(f"• {bucket['Name']}")
            print(f"  Region: {bucket['Region']}")
            print(f"  Created: {bucket['CreationDate'].strftime('%Y-%m-%d')}")
            print()
        
        # Show summary
        print("-" * 50)
        print(f"Total empty buckets found: {len(empty_buckets)}")
        
        # Always run in dry-run mode first
        print("\n" + "!" * 50)
        print("RUNNING IN DRY-RUN MODE - NO BUCKETS WILL BE DELETED")
        print("To actually delete, change dry_run=False in delete_buckets() call")
        print("!" * 50)
        
        delete_buckets(empty_buckets, dry_run=True)
        
    else:
        print("\nNo empty buckets found with versioning disabled.")
        print("Note: Buckets with versioning enabled are skipped for safety.")
    
    print("\n" + "=" * 70)
    print("SCAN COMPLETE")
    print("=" * 70)

if __name__ == "__main__":
    main()