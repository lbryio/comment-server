import json

if __name__ == '__main__':
    with open('comments_on_claims.json', 'r') as fp:
        claims = json.load(fp)

    for claim in claims.values():
        if claim:
            print('\n' + claim['name'])
            comment: dict = {}
            for comment in claim['comments']:
                output = f"\t{comment['channel_name']}: "
                comment: str = comment['comment']
                slices = comment.split('\n')
                for i, slice in enumerate(slices):
                    if len(slice) > 120:
                if '\n' not in comment and len(comment) > 120:
                    parts = []
                    for i in range(0, len(comment), 120):



                else:
                    output += comment.replace('\n', '\n\t\t')
                output += '\n'

                print(output)

            print('_'*256 + '\n')
