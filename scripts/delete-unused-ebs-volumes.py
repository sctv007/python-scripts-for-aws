import boto3

def get_unused_volumes(region_name='us-east-1'):
    # Create a session for a specific profile and region
    session = boto3.Session(profile_name='script-automation-user', region_name=region_name)
    ec2 = session.resource('ec2')
    unused_volumes = []
    for volume in ec2.volumes.all():
        if volume.state == 'available':
            attachments = volume.attachments
            if not attachments:
                volume_id = volume.id.replace('\u00A0', ' ')
                unused_volumes.append(volume_id)
    return unused_volumes

def delete_volumes(volumes, region_name='us-east-1'):
    """Delete specified volumes in a region using secure profile"""
    session = boto3.Session(profile_name='script-automation-user', region_name=region_name)
    ec2 = session.resource('ec2')
    
    for volume in volumes:
        if dry_run:
            print(f"[DRY RUN] Would delete volume {volume}")
        else:
            print(f"Deleting volume {volume}")
            ec2.Volume(volume).delete()

def main():
    initial_session = boto3.Session(profile_name='script-automation-user', region_name='us-east-1')
    ec2_client = initial_session.client('ec2')
    
    regions = [region['RegionName'] for region in ec2_client.describe_regions()['Regions']]
    
    for region in regions:
        print(f"Checking for unused volumes in region {region}")
        unused_volumes = get_unused_volumes(region_name=region)
        
        if unused_volumes:
            # Add dry_run parameter for safety
            delete_volumes(unused_volumes, region_name=region, dry_run=True)
        else:
            print(f"No unused volumes found in region {region}")

if __name__ == "__main__":
    main()