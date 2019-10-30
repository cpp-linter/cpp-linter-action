FILES=`jq -r '.pull_request._links.self.href' "$GITHUB_EVENT_PATH"`/files
echo "Files = $FILES"
echo "Workspace: $GITHUB_WORKSPACE"
cd $GITHUB_WORKSPACE
ls

#curl $FILES > files.json
#FILES_URL=`jq -r '.[].raw_url' files.json`

#echo "File names: $FILES_URL"

#mkdir files
#cd files
#curl $FILES_URL --remote-name-all
