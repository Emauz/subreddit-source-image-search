from data import DataWriter
from typing import Iterable
import os
import urllib.request
import urllib.error
import handlers
import tools
import praw
import prawcore.exceptions
import cv2


def get_download_data_for(url: str) -> Iterable[str]:
    """ Yields a collection of direct content links from the requested url. """

    if url.endswith(".gifv"):
        url = url.replace(".gifv", ".webm")

    if tools.is_file(url):
        yield url

    else:

        if 'imgur' in url:
            images = handlers.imgur(url)

        elif 'gfycat' in url:
            images = handlers.gfycat(url)

        else:
            print("No handler for {}".format(url))
            images = []

        for image in images:
            yield image


def download(url: str, output_path: str) -> bool:
    """ Download the url to the output path, returning if it was successful. """

    download_path = os.path.join(output_path, tools.get_url_filename(url))

    # Abort download if image is animated
    ANIMATED_IMAGE_TYPES = ['gif', 'webm', 'mp4']
    file_type = url.split('.')[-1]
    if file_type in ANIMATED_IMAGE_TYPES:
        print("Aborting download, animated image. {0}".format(url))
        return False

    if not os.path.exists(download_path):
        try:
            urllib.request.urlretrieve(url, download_path)
            return True

        except urllib.error.HTTPError as e:
            # Does not exist
            if e.errno == 404:
                return False

        except urllib.error.URLError as e:
            # Connection did not resolve
            if e.winerror == 10060:
                return False

        except ConnectionResetError as e:
            # Forcibly closed connection;
            # TODO: this can possibly be fixed by adding headers to requests.
            if e.winerror == 10054:
                return False

    return False


def main():
    count, subimage_path, subreddits = tools.get_arguments()
    output_path = tools.make_folder(tools.OUTPUT_FOLDER)
    reddit = praw.Reddit("image-search-bot", user_agent="subreddit-source-image-search (by u/Emauz)")
    tools.make_folder(output_path)
    subimage = cv2.imread(subimage_path)

    for subreddit in subreddits:
        print("-- {0}".format(subreddit))

        try:
            # get every submission
            for submission in reddit.subreddit(subreddit).top("all", limit=count):
                submission_url = submission.url
                response = get_download_data_for(submission_url)

                # download each url
                for url in response:
                    downloaded = download(url, output_path)

                    if downloaded:
                        print("Downloaded {0}.".format(url))
                        image_path = os.path.join(output_path, tools.get_url_filename(url))
                        # Open image and attempt to check if it's parent of target sub-image
                        img = cv2.imread(image_path)
                        try:
                            result = cv2.matchTemplate(subimage, img, cv2.TM_CCOEFF_NORMED)
                            _, max_val, _, _ = cv2.minMaxLoc(result)
                            if max_val > 0.9:
                                print("Found an image! Saved as: {0}".format(image_path))
                            else:
                                os.remove(image_path)
                        except cv2.error:
                            print("cv2 error, unable to compare images.")
                            os.remove(image_path)

        except prawcore.exceptions.NotFound:
            print("{} returned 404, not found. Skipping ...".format(subreddit))


if __name__ == '__main__':
    main()
