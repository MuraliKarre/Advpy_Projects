#!/usr/bin/env python
import json
import argparse

from awacs.sts import AssumeRole
from troposphere import Ref, FindInMap, Template, Tags, Join, \
    GetAtt, ec2, Parameter
from troposphere.ec2 import VPC, Subnet, VPCGatewayAttachment, RouteTable, Route, SubnetRouteTableAssociation, \
    NatGateway

from troposphere.autoscaling import AutoScalingGroup, Tag, LaunchConfiguration
from troposphere.cloudwatch import Alarm, MetricDimension
from troposphere.sns import Subscription, Topic
from awacs.aws import Allow, Statement, Principal, PolicyDocument

from troposphere.iam import Role, InstanceProfile, PolicyType
from troposphere.s3 import Bucket, VersioningConfiguration, \
    LifecycleConfiguration, LifecycleRule, NoncurrentVersionTransition, \
    LifecycleRuleTransition



def create_cloudformation_template(elb=None):
    template = Template()

    template.set_description(
        "AWS CloudFormation Template to create single tier web application.")

    AlarmEmail = template.add_parameter(Parameter(
        "AlarmEmail",
        Default="praveensinghraghav@gmail.com",
        Description="Email address to notify ",
        Type="String",
    ))

    BucketName = template.add_parameter(Parameter(
        "BucketName",
        Description="Bucket Name for logging",
        Type="String"
    ))

    WebServerPort = template.add_parameter(Parameter(
        "WebServerPort",
        Type="String",
        Default="80",
        Description="TCP/IP port of the web server",
    ))

    WebServerIP = template.add_parameter(Parameter(
        "WebServerIP",
        Type="String",
        Description="IP Range for Instance Access",
    ))

    CidrBlockRange = template.add_parameter(Parameter(
        "CidrBlockRange",
        Type="String",
        Default="10.0.0.0/16",
        Description="Cidr Range for VPC",
    ))

    PublicSubnetCidrRange1 = template.add_parameter(Parameter(
        "PublicSubnetCidrRange1",
        Type="String",
        Default="10.0.1.0/24",
        Description="Cidr Range for Public Subnet",
    ))
    PublicSubnetCidrRange2 = template.add_parameter(Parameter(
        "PublicSubnetCidrRange2",
        Type="String",
        Default="10.0.2.0/24",
        Description="Cidr Range for Public Subnet",
    ))

    PrivateSubnetCidrRange = template.add_parameter(Parameter(
        "PrivateSubnetCidrRange",
        Type="String",
        Default="10.0.3.0/24",
        Description="Cidr Range for Private Subnet",
    ))

    KeyName = template.add_parameter(Parameter(
        "KeyName",
        Type="String"
    ))

    S3Bucket = template.add_resource(Bucket(
        "S3Bucket",
        BucketName=Ref(BucketName),
        AccessControl="Private",
        VersioningConfiguration=VersioningConfiguration(
            Status="Enabled",
        ),
        LifecycleConfiguration=LifecycleConfiguration(Rules=[
            LifecycleRule(
                Id="S3BucketRule001",
                Prefix="/",
                Status="Enabled",
                ExpirationInDays=3650,
                Transitions=[
                    LifecycleRuleTransition(
                        StorageClass="STANDARD_IA",
                        TransitionInDays=60,
                    ),
                ],
                NoncurrentVersionExpirationInDays=365,
                NoncurrentVersionTransitions=[
                    NoncurrentVersionTransition(
                        StorageClass="STANDARD_IA",
                        TransitionInDays=30,
                    ),
                    NoncurrentVersionTransition(
                        StorageClass="GLACIER",
                        TransitionInDays=120,
                    ),
                ],
            ),
        ]),

    ))

    def CFNRole():

         CFNRolePolicies = template.add_resource(PolicyType(
        "CFNRolePolicies",
        PolicyName="CFNUsers",
        Roles=[Ref(CFNRole)],
        PolicyDocument={
            "Version": "2012-10-17",
            "Statement": [{
                "Effect": "Allow",
                "Action": [
                    "s3:PutObject"
                ],
                "Resource": Join("", ["arn:aws:s3:::", GetAtt(BucketName, 'Name'), "/*"])
            }],
        }
    ))

    CFNInstanceProfile = template.add_resource(InstanceProfile(
        "CFNInstanceProfile",
        Roles=[Ref(CFNRole)]
    ))

    Vpc = template.add_resource(VPC(
        "VPC",
        CidrBlock=Ref(CidrBlockRange),
        Tags=Tags(
            Name="VPC"
        )
    ))

    CFNRole = template.add_resource(Role(
        "CFNRole",
        AssumeRolePolicyDocument=PolicyDocument(
            Statement=[
                Statement(
                    Effect=Allow,
                    Action=[AssumeRole],
                    Principal=Principal("Service", ["ec2.amazonaws.com"])
                )
            ]
        )
    ))

    GatewayAttachment = template.add_resource(VPCGatewayAttachment(
        "InternetGatewayAttachment",
        VpcId=Ref(Vpc)
    ))

    PublicSubnet1 = template.add_resource(Subnet(
        "PublicSubnet1",
        VpcId=Ref(Vpc),
        AvailabilityZone=Join(" ", [Ref("AWS::Region"), "a"]),
        CidrBlock=Ref(PublicSubnetCidrRange1),
        MapPublicIpOnLaunch=True,
        Tags=Tags(
            Name="PublicSubnet"
        )
    ))

    PublicSubnet2 = template.add_resource(Subnet(
        "PublicSubnet2",
        VpcId=Ref(Vpc),
        AvailabilityZone=Join(" ", [Ref("AWS::Region"), "b"]),
        CidrBlock=Ref(PublicSubnetCidrRange2),
        MapPublicIpOnLaunch=True,
        Tags=Tags(
            Name="PublicSubnet"
        )
    ))

    def NatGatewayEIP():
        NatGateway = template.add_resource(ec2.NatGateway(
        "NatGateway",
        AllocationId=GetAtt(NatGatewayEIP, 'AllocationId'),
        SubnetId=Ref(PublicSubnet1)
    ))

    PublicRouteTable = template.add_resource(RouteTable(
        "PublicRouteTable",
        VpcId=Ref(Vpc),
        Tags=Tags(
            Name="PublicRoute"
        )
    ))

    template.add_resource(Route(
        "DefaultPublicRoute",
        DependsOn=GatewayAttachment.title,
        RouteTableId=Ref(PublicRouteTable),
        DestinationCidrBlock="0.0.0.0/0",
    ))

    template.add_resource(SubnetRouteTableAssociation(
        "PublicSubnetRouteTableAssociation1",
        RouteTableId=Ref(PublicRouteTable),
        SubnetId=Ref(PublicSubnet1)
    ))

    template.add_resource(SubnetRouteTableAssociation(
        "PublicSubnetRouteTableAssociation2",
        RouteTableId=Ref(PublicRouteTable),
        SubnetId=Ref(PublicSubnet2)
    ))

    PrivateSubnet = template.add_resource(Subnet(
        "PrivateSubnet",
        VpcId=Ref(Vpc),
        AvailabilityZone=Join(" ", [Ref("AWS::Region"), "a"]),
        CidrBlock=Ref(PrivateSubnetCidrRange),
        Tags=Tags(
            Name="PrivateSubnet"
        )
    ))

    PrivateRouteTable = template.add_resource(RouteTable(
        "PrivateRouteTable",
        VpcId=Ref(Vpc),
        Tags=Tags(
            Name="PrivateRoute"
        )
    ))

    template.add_resource(Route(
        "DefaultPrivateRoute",
        RouteTableId=Ref(PrivateRouteTable),
        DestinationCidrBlock="0.0.0.0/0",
        NatGatewayId=Ref(NatGateway)
    ))

    template.add_resource(SubnetRouteTableAssociation(
        "PrivateSubnetRouteTableAssociation",
        RouteTableId=Ref(PrivateRouteTable),
        SubnetId=Ref(PrivateSubnet)
    ))

    SecurityGroup = template.add_resource(ec2.SecurityGroup(
        "SecurityGroup",
        GroupDescription="Allow http to client host",
        VpcId=Ref(Vpc),
        SecurityGroupIngress=[
            ec2.SecurityGroupRule(
                IpProtocol="tcp",
                FromPort=Ref(WebServerPort),
                ToPort=Ref(WebServerPort),
                CidrIp=Ref(WebServerIP),
            )]
    ))

    LaunchConfig = template.add_resource(LaunchConfiguration(
        "LaunchConfigration",
        ImageId=FindInMap("RegionMap", Ref("AWS::Region"), "64"),
        InstanceType="t2.micro",
        SecurityGroups=[Ref(SecurityGroup)],
        IamInstanceProfile=Ref(CFNInstanceProfile),
        KeyName=Ref(KeyName),
    ))

    # ApplicationElasticLB = template.add_resource(
    #     "ALB"
    #
    # )
    #
    # TargetGroupWeb = template.add_resource(
    #     "Target Group to be attached"
    #
    # )

    AutoScalingGroups = template.add_resource(AutoScalingGroup(
        "AutoScalingGroups",
        VPCZoneIdentifier=[Ref(PrivateSubnet)],
        LaunchConfigurationName=Ref(LaunchConfig),
        MinSize="1",
        MaxSize="5",
        DesiredCapacity="1",
        TargetGroupARNs=[Ref(TargetGroupWeb)]
    ))

    Listener = template.add_resource(elb.Listener(
        "Listener",
        Port=Ref(WebServerPort),
        Protocol="HTTP",
        LoadBalancerArn=Ref(ApplicationElasticLB),
        DefaultActions=[elb.Action(
            Type="forward",
            TargetGroupArn=Ref(TargetGroupWeb)
        )]
    ))

    AlarmTopic = template.add_resource(Topic(
        "AlarmTopic",
        Subscription=[Subscription(
            Protocol="email",
            Endpoint=Ref(AlarmEmail)
        )]
    ))

    InstanceAlarm = template.add_resource(Alarm(
        "InstanceCPUUsageAlarm",
        AlarmDescription="Alarm if queue depth grows beyond 10 messages",
        Namespace="AWS/EC2",
        MetricName="CPUUtilization",
        Dimensions=[
            MetricDimension(
                Name="AutoScalingGroupName",
                Value=Ref(AutoScalingGroups)
            ),
        ],
        Statistic="Average",
        Period="300",
        EvaluationPeriods="1",
        Threshold="50",
        ComparisonOperator="GreaterThanThreshold",
        AlarmActions=[Ref(AlarmTopic), ],
        InsufficientDataActions=[
            Ref(AlarmTopic), ],
    ))

    f = open("simplAssigment.yml", "w")
    f.write(template.to_yaml())
    f.close()


def create_cloudformation_stack(args):

    return response


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process some integers.')

    parser.add_argument("-a", "--AlarmEmail", required=True,
                        help="Email address to notify")
    parser.add_argument("-b", "--BucketName", required=True,
                        help="Bucket Name for logging")
    parser.add_argument("-c", "--CidrBlockRange", required=True,
                        help="Cidr Range for VPC")
    parser.add_argument("-k", "--KeyName", required=True,
                        help="Key Pair Name for EC2")
    parser.add_argument("-pr", "--PrivateSubnetCidrRange", required=True,
                        help="Cidr Range for Private Subnet")
    parser.add_argument("-ps1", "--PublicSubnetCidrRange1", required=True,
                        help="Cidr Range for Public Subnet1")
    parser.add_argument("-ps2", "--PublicSubnetCidrRange2", required=True,
                        help="Cidr Range for Public Subnet2")
    parser.add_argument("-wp", "--WebServerIP", required=True,
                        help="IP Range for Instance Access")
    parser.add_argument("-wsp", "--WebServerPort", required=True,
                        help="TCP/IP port of the web server")

    args = vars(parser.parse_args())
    create_cloudformation_template()
    response = create_cloudformation_stack(args)
    print(json.dumps(response))
