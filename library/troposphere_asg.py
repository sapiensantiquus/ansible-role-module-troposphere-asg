from troposphere import Base64, Join
from troposphere import Parameter, Ref, Template
from troposphere import cloudformation, autoscaling
from troposphere.autoscaling import AutoScalingGroup, Tag
from troposphere.autoscaling import LaunchConfiguration
from troposphere.elasticloadbalancing import LoadBalancer
from troposphere.policies import UpdatePolicy, AutoScalingRollingUpdate
import troposphere.ec2 as ec2
import troposphere.elasticloadbalancing as elb
import boto3

t = Template()

t.add_description("Configures autoscaling group")

SecurityGroup = t.add_parameter(Parameter(
    "SecurityGroup",
    Type="String",
    Description="Security Group ID",
))

KeyName = t.add_parameter(Parameter(
    "KeyName",
    Type="String",
    Description="Name of an existing EC2 KeyPair to enable SSH access",
    MinLength="1",
    AllowedPattern="[\x20-\x7E]*",
    MaxLength="255",
    ConstraintDescription="can contain only ASCII characters.",
))

ScaleCapacity = t.add_parameter(Parameter(
    "ScaleCapacity",
    Default="1",
    Type="String",
    Description="Number of api servers to run",
))

AmiId = t.add_parameter(Parameter(
    "AmiId",
    Type="String",
    Description="The AMI id for the api instances",
))

VPCAvailabilityZones = t.add_parameter(Parameter(
    "VPCAvailabilityZones",
    Type="List<AWS::EC2::AvailabilityZone::Name>",
    Description="First availability zone",
))

StackName = t.add_parameter(Parameter(
    "StackName",
    Type="String",
    Description="The root stack name",
))

SubnetIDs = t.add_parameter(Parameter(
    "SubnetIDs",
    Type="List<AWS::EC2::Subnet::Id>",
    Description="Second private VPC subnet ID for the api app.",
))

LaunchConfiguration = t.add_resource(LaunchConfiguration(
    "LaunchConfiguration",
    Metadata=autoscaling.Metadata(
        cloudformation.Init({
            "config": cloudformation.InitConfig(
                packages={
                    "apt" : {
                        "python-pip" : [],
                        "p7zip-full": []
                    },
                    "pip" :{
                        "awscli" : []
                    }
                }
            )
        })
    ),
    UserData=Base64(Join('', [
        "#!/bin/bash\n",
        "cfn-signal -e 0",
        "    --resource AutoscalingGroup",
        "    --stack ", Ref("AWS::StackName"),
        "    --region ", Ref("AWS::Region"), "\n"
    ])),
    ImageId=Ref(AmiId),
    KeyName=Ref(KeyName),
    BlockDeviceMappings=[
        ec2.BlockDeviceMapping(
            DeviceName="/dev/sda1",
            Ebs=ec2.EBSBlockDevice(
                VolumeSize="8"
            )
        ),
    ],
    SecurityGroups=[Ref(SecurityGroup)],
    InstanceType="m3.medium",
))

asg = t.add_resource(AutoScalingGroup(
    "AutoscalingGroup",
    DesiredCapacity=Ref(ScaleCapacity),
    LaunchConfigurationName=Ref(LaunchConfiguration),
    MinSize=Ref(ScaleCapacity),
    MaxSize=Ref(ScaleCapacity),
    VPCZoneIdentifier=Ref(SubnetIDs),
    AvailabilityZones=Ref(VPCAvailabilityZones),
    HealthCheckType="EC2",
    UpdatePolicy=UpdatePolicy(
        AutoScalingRollingUpdate=AutoScalingRollingUpdate(
            PauseTime='PT5M',
            MinInstancesInService="1",
            MaxBatchSize='1',
            WaitOnResourceSignals=True
        )
    )
))

parameters = {
    'SubnetIDs' : "subnet-3da5654b, subnet-71c4d728",
    'VPCAvailabilityZones' : "us-west-2a, us-west-2c",
    'SecurityGroup' : 'sg-a16656c6',
    'KeyName' : 'global-mgage-logging-ansible',
    'StackName' : 'asg_test',
    'AmiId' : 'ami-8d42beed'
 }

parameters_aws = []
for key in parameters:
    d = {
        'ParameterKey' : key,
        'ParameterValue' : parameters[key]
    }
    parameters_aws.append(d)

cfn_client = boto3.client('cloudformation')
cfn_client.create_stack(StackName='asg-test',TemplateBody=t.to_json(),Parameters=parameters_aws)
