#!/usr/bin/env python3
import aws_cdk as cdk
from e_com67 import ECom67Stack 

app = cdk.App()
ECom67Stack(app, "e-com67Stack", 
    env=cdk.Environment(
        account='724542698940',
        region='ap-southeast-1'
    )
)

app.synth()