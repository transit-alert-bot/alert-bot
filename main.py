import os, re

from atproto import (
    CAR,
    AtUri,
    Client,
    client_utils,
    FirehoseSubscribeReposClient,
    firehose_models,
    models,
    parse_subscribe_repos_message,
)
from dotenv import load_dotenv
import requests

# Load environment variables
load_dotenv()

# Bluesky credentials
BLUESKY_USERNAME = os.getenv("BLUESKY_USERNAME")
BLUESKY_PASSWORD = os.getenv("BLUESKY_PASSWORD")

API_URL = os.getenv("IMAGINE_URL")
COPYPASTA_API_URL = os.getenv("IMAGINE_COPYPASTA_URL")

# Create a Bluesky client
client = Client("https://bsky.social")
firehose = FirehoseSubscribeReposClient()

def get_file_extension(file_path):
    return os.path.splitext(file_path)[1]

def name_in_text(text: str) -> bool:
    return re.search(r'cc: dreambot', text, re.IGNORECASE) is not None

def extract_prompt(input_string: str) -> str:
    pattern = r'(?i)\bgenerate\s*:\s*(.*)'  # Regex pattern to match variations of "generate:"
    match = re.search(pattern, input_string)
    if match:
        return match.group(1).strip()  # Return the matched text, stripping leading and trailing whitespace
    else:
        return "Substring not found in the input string."

def extract_prompt_from_parent(input_string: str) -> str:
    pattern = r'(?i)\b(?:generate|update)\s*:\s*(.*)'  # Updated regex pattern to match variations of "generate:" and "update:" in a case-insensitive manner with optional whitespace after the colon
    match = re.search(pattern, input_string)
    if match:
        return match.group(1).strip()  # Return the matched text, stripping leading and trailing whitespace
    else:
        return "Substring not found in the input string. parent"


def parse_thread(author_did, thread):
    entries = []
    stack = [thread]

    while stack:
        current_thread = stack.pop()

        if current_thread is None:
            continue

        if current_thread.post.author.did == author_did:
            print("parse thread\n")
            print(current_thread.post.record.text)
            entries.append(extract_prompt_from_parent(current_thread.post.record.text))

        stack.append(current_thread.parent)

    return entries


def generate_image(prompts):
    try:
        response = requests.post(API_URL, json={"prompts": prompts})
        response.raise_for_status()  # Raises exception for 4xx and 5xx status codes
        return response.content
    except requests.RequestException as e:
        print(f"Error generating image: {e}")
        return None

def process_operation(
    op: models.ComAtprotoSyncSubscribeRepos.RepoOp,
    car: CAR,
    commit: models.ComAtprotoSyncSubscribeRepos.Commit,
) -> None:
    uri = AtUri.from_str(f"at://{commit.repo}/{op.path}")

    if op.action == "create":
        if not op.cid:
            return

        record = car.blocks.get(op.cid)
        if not record:
            return

        record = {
            "uri": str(uri),
            "cid": str(op.cid),
            "author": commit.repo,
            **record,
        }

        if uri.collection == models.ids.AppBskyFeedPost:
            if name_in_text(record["text"]):
                poster_profile = client.get_profile(actor=record["author"])
                posts_in_thread = client.get_post_thread(uri=record["uri"])
                # if record.get("reply"):
                #     if record["reply"]["root"]["uri"]:
                #         posts_in_thread = client.get_post_thread(uri=record["reply"]["root"]["uri"])
                print("Posts in thread: ", posts_in_thread.model_dump_json())
                # check if the bot was tagged in post or reply
                entries = []
                if posts_in_thread.thread.parent == None:
                    entries.append(extract_prompt(record["text"]))
                else:
                    entries.append(extract_prompt_from_parent(record["text"]))
                    entries.extend(parse_thread(posts_in_thread.thread.post.author.did, posts_in_thread.thread.parent))

                print("Prompt: ", entries)

                img = generate_image(entries)
                # send a reply to the post
                record_ref = {"uri": record["uri"], "cid": record["cid"]}
                reply_ref = models.AppBskyFeedPost.ReplyRef(
                    parent=record_ref, root=record_ref
                )
                response_text = client_utils.TextBuilder()
                response_text.text(f"Hey, @{poster_profile.handle}. Here's a image generated from your post. ")
                # response_text.mention('account', posts_in_thread.thread.post.author.did)
                # response_text.link('link', "https://oaidalleapiprodscus.blob.core.windows.net/private/org-tk2WweVzkr4IDSoWN3yXPYah/user-YlKkZu9RNJ7Ioaely2LTeGZa/img-89edeK9NCX5t2STXHDoJfNsD.png?st=2024-02-25T19%3A28%3A33Z&se=2024-02-25T21%3A28%3A33Z&sp=r&sv=2021-08-06&sr=b&rscd=inline&rsct=image/png&skoid=6aaadede-4fb3-4698-a8f6-684d7786b067&sktid=a48cca56-e6da-484e-a814-9c849652bcb3&skt=2024-02-25T18%3A17%3A56Z&ske=2024-02-26T18%3A17%3A56Z&sks=b&skv=2021-08-06&sig=hvrnOK7efFk9pEPF/eMLix0Hip1IgRcHR8tb9Em6z5w%3D")
                client.send_image(
                    text=response_text,
                    reply_to=reply_ref,
                    image=img,
                    image_alt=entries[-1].strip(),
                )
                return




    if op.action == "delete":
        # Process delete(s)
        return

    if op.action == "update":
        # Process update(s)
        return

    return


# No need to edit this function - it processes messages from the firehose
def on_message_handler(message: firehose_models.MessageFrame) -> None:
    commit = parse_subscribe_repos_message(message)
    if not isinstance(
        commit, models.ComAtprotoSyncSubscribeRepos.Commit
    ) or not isinstance(commit.blocks, bytes):
        return

    car = CAR.from_bytes(commit.blocks)

    for op in commit.ops:
        process_operation(op, car, commit)


def main() -> None:
    client.login(BLUESKY_USERNAME, BLUESKY_PASSWORD)
    print("🤖 Bot is listening")
    firehose.start(on_message_handler)

if __name__ == "__main__":
    main()
