import boto3

def get_unused_elastic_ips(region_name='us-east-1'):
    """
    Find unused Elastic IP addresses in a specific AWS region.
    
    Unused EIPs are those allocated to your account but not associated
    with any running instance or network interface.
    """
    session = boto3.Session(profile_name='script-automation-user', region_name=region_name)
    ec2 = session.client('ec2')
    
    try:
        # Describe all Elastic IPs in the VPC
        response = ec2.describe_addresses(Filters=[{"Name": "domain", "Values": ["vpc"]}])
        unused_ips = []
        
        for address in response['Addresses']:
            # If no AssociationId, the EIP is not attached to anything
            if 'AssociationId' not in address:
                unused_ips.append({
                    'PublicIp': address.get('PublicIp', 'Unknown'),
                    'AllocationId': address['AllocationId'],
                    'NetworkInterfaceId': address.get('NetworkInterfaceId'),
                    'PrivateIpAddress': address.get('PrivateIpAddress')
                })
        
        return unused_ips
        
    except Exception as e:
        print(f"Error scanning Elastic IPs in {region_name}: {e}")
        return []

def release_elastic_ips(ip_list, region_name='us-east-1', dry_run=True):
    """
    Release (delete) Elastic IP addresses.
    
    WARNING: Once released, Elastic IPs cannot be recovered.
    """
    if not ip_list:
        print(f"No Elastic IPs to release in {region_name}")
        return
    
    session = boto3.Session(profile_name='script-automation-user', region_name=region_name)
    ec2 = session.client('ec2')
    
    released_count = 0
    for ip_info in ip_list:
        public_ip = ip_info['PublicIp']
        allocation_id = ip_info['AllocationId']
        
        if dry_run:
            print(f"[DRY RUN] Would release Elastic IP {public_ip} ({allocation_id}) in {region_name}")
        else:
            try:
                ec2.release_address(AllocationId=allocation_id)
                print(f"Released Elastic IP {public_ip} ({allocation_id}) in {region_name}")
                released_count += 1
            except Exception as e:
                print(f"Failed to release Elastic IP {public_ip}: {e}")
    
    if not dry_run:
        print(f"Successfully released {released_count} Elastic IP(s) in {region_name}")

def main():
    """Main function to scan all regions for unused Elastic IPs"""
    # Get initial session to list regions
    session = boto3.Session(profile_name='script-automation-user', region_name='us-east-1')
    ec2_client = session.client('ec2')
    
    # Get all AWS regions
    regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
    
    print("=" * 60)
    print("Elastic IP Cleanup Script")
    print("=" * 60)
    print(f"Scanning {len(regions)} AWS regions...")
    print("Note: Running in DRY RUN mode by default (no changes will be made)")
    print("To actually release IPs, change dry_run=False in the release_elastic_ips() call")
    print("=" * 60)
    
    total_unused = 0
    
    for region in regions:
        print(f"\nChecking region: {region}")
        unused_ips = get_unused_elastic_ips(region_name=region)
        
        if unused_ips:
            print(f"Found {len(unused_ips)} unused Elastic IP(s) in {region}:")
            for ip_info in unused_ips:
                print(f"  - {ip_info['PublicIp']} (Private: {ip_info.get('PrivateIpAddress', 'N/A')})")
            
            # Release the IPs (with dry_run=True for safety)
            release_elastic_ips(unused_ips, region_name=region, dry_run=True)
            total_unused += len(unused_ips)
        else:
            print(f"No unused Elastic IPs found in {region}")
    
    print("\n" + "=" * 60)
    print(f"SCAN COMPLETE: Found {total_unused} total unused Elastic IPs across all regions")
    
    if total_unused > 0:
        monthly_savings = total_unused * 3.65  # AWS charges ~$3.65/month per unattached EIP
        print(f"Potential monthly savings: ${monthly_savings:.2f} USD")
        print("\n⚠️  WARNING: Elastic IPs cannot be recovered after release!")
        print("   Make sure you don't need these IPs before disabling dry-run mode.")
    print("=" * 60)

if __name__ == "__main__":
    main()