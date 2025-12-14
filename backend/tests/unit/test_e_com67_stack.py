import aws_cdk as core
import aws_cdk.assertions as assertions

from e_com67.e_com67_stack import ECom67Stack

# example tests. To run these tests, uncomment this file along with the example
# resource in e_com67/e_com67_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = ECom67Stack(app, "e-com67")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
