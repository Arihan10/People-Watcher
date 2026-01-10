import React, { useState, useEffect, useRef } from "react";
import axios from "axios";
import "./App.css";

const API = "/api";

const SPACES = [
	{
		name: "Secluded Garden",
		objects: ["flower_beds", "bench", "willow_tree", "pond"],
	}, // Romantic setting
	{
		name: "Town Tavern",
		objects: ["bar_counter", "tables", "mugs", "dartboard"],
	}, // Confrontational setting
	{
		name: "Private Bedroom",
		objects: ["bed", "candles", "mirror", "dresser"],
	}, // Intimate setting
];

// Using specific characters with interesting relationships
// Will try to find: Marcus (crush on Isabella), Isabella, Aldric (confrontational), Thomas

function App() {
	const [view, setView] = useState("simulation"); // 'simulation' or 'testing'
	const [characters, setCharacters] = useState([]);
	const [allCharacters, setAllCharacters] = useState([]);
	const [characterPositions, setCharacterPositions] = useState({});
	const [logs, setLogs] = useState([]);
	const [activeConversations, setActiveConversations] = useState([]);
	const [selectedCharacter, setSelectedCharacter] = useState(null);

	// Testing state
	const [testResults, setTestResults] = useState({});

	useEffect(() => {
		loadCharacters();
	}, []);

	const loadCharacters = async () => {
		try {
			const res = await axios.get(`${API}/characters`);
			setAllCharacters(res.data);

			// Load characters with ROMANTIC TENSION for testing romance conversations
			const antonio = res.data.find((c) => c.name === "Antonio Martinez");
			const denise = res.data.find((c) => c.name === "Denise Thompson");
			const miguel = res.data.find((c) => c.name === "Miguel Rodriguez");
			const sofia = res.data.find((c) => c.name === "Sofia Martinez");

			// Romantic pairs: Antonio+Denise (mutual slow-burn), Miguel+Sofia (unrequited turning mutual)
			const focused = [antonio, denise, miguel, sofia].filter(Boolean);

			// Fall back to first 4 if specific ones not found
			if (focused.length < 4) {
				focused.push(
					...res.data
						.filter((c) => !focused.includes(c))
						.slice(0, 4 - focused.length)
				);
			}

			setCharacters(focused);

			addLog(`🌍 Loaded ${res.data.length} characters total`);
			addLog(`   💕 ROMANTIC TENSION TEST - Focusing on:`);
			if (antonio && denise) {
				addLog(
					`      - Antonio + Denise: Slow-burning romance (mutual 65 score)`
				);
			}
			if (miguel && sofia) {
				addLog(
					`      - Miguel + Sofia: Miguel loves Sofia (70), Sofia developing feelings (60)`
				);
			}
			focused.forEach((c) => {
				const traits =
					c.personality_traits?.slice(0, 2).join(", ") || "";
				addLog(`      - ${c.name} (${traits})`);
			});

			// Strategic positioning for ROMANCE scenarios:
			// Put romantic pairs together in romantic settings
			const positions = {};

			// Place Antonio + Denise together at Town Square (for romantic meeting)
			if (antonio && denise) {
				positions[antonio._id] = "Town Square";
				positions[denise._id] = "Town Square";
				addLog(
					`   💕 Antonio & Denise at Town Square (slow-burn romance!)`
				);
			}

			// Place Miguel + Sofia together at The Inn (for intimate conversation)
			if (miguel && sofia) {
				positions[miguel._id] = "The Sleeping Dragon Inn";
				positions[sofia._id] = "The Sleeping Dragon Inn";
				addLog(
					`   💕 Miguel & Sofia at The Inn (unrequited love turning mutual!)`
				);
			}

			// Fill remaining
			focused.forEach((char, i) => {
				if (!positions[char._id]) {
					positions[char._id] = SPACES[i % SPACES.length].name;
				}
			});

			setCharacterPositions(positions);
			addLog(`   Positions initialized for ROMANCE TEST 💕`);

			// Clear any stale conversation data
			setActiveConversations([]);
			conversationTurnIndexRef.current = 0;
		} catch (error) {
			console.error("Error loading characters:", error);
			addLog(`❌ Failed to load characters: ${error.message}`);
		}
	};

	const addLog = (message, highlight = false) => {
		setLogs((prev) =>
			[
				...prev,
				{
					time: new Date().toLocaleTimeString(),
					message,
					highlight,
				},
			].slice(-100)
		);
	};

	const getCharactersInSpace = (spaceName) => {
		return characters.filter(
			(c) => characterPositions[c._id] === spaceName
		);
	};

	const getNearbyCharacters = (character, spaceName) => {
		return getCharactersInSpace(spaceName).filter(
			(c) => c._id !== character._id
		);
	};

	// Track which character should speak next in conversation
	const conversationTurnIndexRef = useRef(0);

	const makeCharacterDecide = async (character) => {
		if (!character) return;
		await characterDecisionCycle(character);
	};

	const nextTurn = async () => {
		const activeConvo = activeConversations.find((c) => c.is_active);

		if (activeConvo) {
			// In conversation - alternate between participants
			const turnIndex = conversationTurnIndexRef.current;
			const currentTurnChar = characters.find(
				(c) => c._id === activeConvo.participants[turnIndex]
			);

			if (currentTurnChar) {
				await makeCharacterDecide(currentTurnChar);

				// Switch turn
				conversationTurnIndexRef.current =
					(turnIndex + 1) % activeConvo.participants.length;
			}
		} else {
			// No conversation - use selected character or first available
			const char = selectedCharacter || characters[0];
			if (char) {
				await makeCharacterDecide(char);
			}
		}
	};

	const characterDecisionCycle = async (character, customTrigger = null) => {
		const currentSpace = characterPositions[character._id];

		if (!currentSpace) {
			addLog(`   ❌ ${character.name} has no location set`);
			return;
		}

		const nearbyChars = getNearbyCharacters(character, currentSpace);
		const space = SPACES.find((s) => s.name === currentSpace);

		// Determine trigger based on context
		let trigger = customTrigger;
		if (!trigger) {
			const isInConvo = activeConversations.some(
				(c) => c.is_active && c.participants?.includes(character._id)
			);
			if (isInConvo) {
				trigger = "conversation turn";
			} else if (nearbyChars.length > 0) {
				trigger = `proximity to ${nearbyChars
					.map((c) => c.name)
					.join(", ")}`;
			} else {
				trigger = "re-evaluating current situation";
			}
		}

		addLog(`\n🎯 ${character.name}'s Turn`, true);
		addLog(`   Trigger: ${trigger}`);
		addLog(`   Location: ${currentSpace}`);
		addLog(`   Desire: ${character.current_desire || "none"}`);
		addLog(
			`   Happiness: ${character.needs?.happiness}/100, Energy: ${character.needs?.energy}/100`
		);

		const charsInSpace = getCharactersInSpace(currentSpace);
		let spaceDescription = "";

		if (charsInSpace.length > 0) {
			try {
				const ctxRes = await axios.post(
					`${API}/context/generate-space-context`,
					{
						space_name: currentSpace,
						characters_present: charsInSpace.map((c) => c.name),
						available_objects: space?.objects || [],
						description: spaceDescription, // Pass existing description
					}
				);
				spaceDescription = ctxRes.data.description;
				if (spaceDescription) {
					addLog(`   📍 Scene: "${spaceDescription}"`);
				}
			} catch (error) {
				console.error("Space context error:", error);
			}
		}

		try {
			// Build space states - show current space + all visible spaces
			// This helps AI know where objects/people are located
			const spaceStates = [
				{
					space_name: currentSpace,
					description: spaceDescription,
					characters_present: charsInSpace.map((c) => c.name),
					available_objects: space?.objects || [],
				},
			];

			// Add other spaces as visible (but character not in them)
			SPACES.filter((s) => s.name !== currentSpace).forEach(
				(otherSpace) => {
					const charsInOtherSpace = getCharactersInSpace(
						otherSpace.name
					);
					spaceStates.push({
						space_name: otherSpace.name,
						description: "", // Could generate if needed
						characters_present: charsInOtherSpace.map(
							(c) => c.name
						),
						available_objects: otherSpace.objects,
					});
				}
			);

			// Build global context - all spaces and character locations
			const characterLocations = characters.map((c) => ({
				character_name: c.name,
				space_name: characterPositions[c._id] || "Unknown",
			}));

			const decisionRes = await axios.post(
				`${API}/characters/${character._id}/decide`,
				{
					trigger_source: trigger,
					space_states: spaceStates,
					global_context: {
						time: "afternoon",
						all_spaces: SPACES.map((s) => s.name),
						character_locations: characterLocations,
					},
				}
			);

			const decision = decisionRes.data;
			addLog(`   🧠 AI Decision: ${decision.reasoning}`);
			addLog(`   📤 Action: ${decision.action.actionType}`);

			await executeAction(character, decision.action, currentSpace);

			// Handle conversation-related actions
			const conversationActions = [
				"speak_in_conversation",
				"fight_in_conversation",
				"romance_in_conversation",
			];

			if (conversationActions.includes(decision.action.actionType)) {
				const dialogue =
					decision.action.props.dialogue ||
					decision.action.props.action;

				if (decision.action.actionType === "speak_in_conversation") {
					addLog(`   💬 "${dialogue}"`);
				} else if (
					decision.action.actionType === "fight_in_conversation"
				) {
					addLog(`   👊 *${dialogue}*`, true);
				} else if (
					decision.action.actionType === "romance_in_conversation"
				) {
					addLog(`   💕 *${dialogue}*`, true);
				}

				// Refresh conversation to get updated turn and session ID
				// Check if we already track this conversation
				let activeConvo = activeConversations.find((c) =>
					c.participants?.includes(character._id)
				);

				// If not tracking (e.g., just started by backend), fetch all sessions to find it
				if (!activeConvo) {
					try {
						// Fetch all active sessions to find the new one
						const sessionsRes = await axios.get(
							`${API}/interaction-sessions/`
						);
						const newSession = sessionsRes.data.find(
							(s) =>
								s.is_active &&
								s.participants.includes(character._id)
						);

						if (newSession) {
							addLog(
								`   ✨ New conversation detected with ${newSession.participant_names.find(
									(n) => n !== character.name
								)}`
							);
							setActiveConversations((prev) => [
								...prev,
								newSession,
							]);
							activeConvo = newSession;
						}
					} catch (err) {
						console.error("Error fetching sessions:", err);
					}
				}

				if (activeConvo) {
					const sessionRes = await axios.get(
						`${API}/interaction-sessions/${activeConvo._id}`
					);
					const updated = sessionRes.data;

					setActiveConversations((prev) =>
						prev.map((c) =>
							c._id === activeConvo._id ? updated : c
						)
					);

					const msgCount = updated.messages?.length || 0;

					// Switch turn
					conversationTurnIndexRef.current =
						(conversationTurnIndexRef.current + 1) %
						activeConvo.participants.length;
					const nextChar = characters.find(
						(c) =>
							c._id ===
							activeConvo.participants[
								conversationTurnIndexRef.current
							]
					);

					addLog(
						`   ✅ Message ${msgCount} | Next: ${nextChar?.name}`
					);

					// Auto-advance to next person's turn after 1 second
					setTimeout(() => nextTurn(), 1000);
				}
			} else if (
				decision.action.actionType === "leave_conversation" ||
				(activeConversations.some((c) =>
					c.participants?.includes(character._id)
				) &&
					["move", "use_object"].includes(decision.action.actionType))
			) {
				// Conversation ended (explicit or implicit)
				addLog(
					`   ✅ ${character.name} ended conversation - AI generating summary`,
					true
				);
				setActiveConversations((prev) =>
					prev.filter((c) => !c.participants?.includes(character._id))
				);
				conversationTurnIndexRef.current = 0; // Reset for next conversation
			}

			const charRes = await axios.get(
				`${API}/characters/${character._id}`
			);
			setCharacters((prev) =>
				prev.map((c) => (c._id === character._id ? charRes.data : c))
			);
		} catch (error) {
			console.error("Decision error:", error);
			console.error("Character ID was:", character._id);
			console.error("Full error:", error.response?.data);
			const errorMsg =
				error.response?.data?.detail ||
				error.message ||
				JSON.stringify(error);
			addLog(`   ❌ Decision failed: ${errorMsg}`);
			addLog(`   Character ID: ${character._id}`);
		}
	};

	const executeAction = async (character, action, currentSpace) => {
		const { actionType, props } = action;

		if (actionType === "move" && props.destination) {
			setCharacterPositions((prev) => ({
				...prev,
				[character._id]: props.destination,
			}));
			const typeInfo = props.destination_type ? ` (${props.destination_type})` : '';
			addLog(`   🚶 ${character.name} → ${props.destination}${typeInfo}`);
		} else if (
			actionType === "initiate_conversation" &&
			props.target_character
		) {
			const targetChar = characters.find(
				(c) => c.name === props.target_character
			);

			if (targetChar) {
				const isBusy = activeConversations.some(
					(c) =>
						c.is_active && c.participants?.includes(targetChar._id)
				);

				if (isBusy) {
					addLog(`   ⏳ ${props.target_character} is busy`);
				} else {
					await startConversation(character, targetChar);
				}
			}
		} else if (
			actionType === "speak_in_conversation" ||
			actionType === "fight_in_conversation" ||
			actionType === "romance_in_conversation"
		) {
			// Message already logged above
		} else if (actionType === "leave_conversation") {
			// Already logged above
		} else if (actionType === "use_object" && props.object_name) {
			try {
				const res = await axios.post(
					`${API}/characters/${character._id}/use/${props.object_name}`
				);
				addLog(`   🎮 ${character.name}: ${res.data.flavor_text}`);
			} catch (error) {
				console.error("Use object error:", error);
			}
		} else if (actionType === "wait") {
			addLog(`   ⏸️ ${character.name} observing`);
		} else {
			addLog(`   💭 ${character.name} continues`);
		}
	};

	const startConversation = async (char1, char2) => {
		try {
			const res = await axios.post(`${API}/interaction-sessions/`, {
				character_ids: [char1._id, char2._id],
				interaction_type: "dialog",
			});

			// Immediately update state
			setActiveConversations((prev) => {
				const updated = [...prev, res.data];
				return updated;
			});

			// Reset turn to participant 0 for this conversation
			conversationTurnIndexRef.current = 0;

			addLog(`   💬 Started conversation: ${char1.name} & ${char2.name}`);
			addLog(`   Session ID: ${res.data._id}`);

			// Auto-start first turn after 1 second
			setTimeout(() => nextTurn(), 1000);
		} catch (error) {
			const errorMsg = error.response?.data?.detail || error.message;
			addLog(`   ❌ Conversation failed: ${errorMsg}`);
		}
	};

	// Removed advanceConversation - .decide() now handles everything

	const reset = async () => {
		setLogs([]);
		setActiveConversations([]);
		conversationTurnIndexRef.current = 0;
		setSelectedCharacter(null);
		await loadCharacters();
	};

	// TESTING FUNCTIONS
	const testGetCharacters = async () => {
		try {
			const res = await axios.get(`${API}/characters`);
			setTestResults((prev) => ({
				...prev,
				getChars: {
					success: true,
					count: res.data.length,
					data: res.data[0],
				},
			}));
		} catch (error) {
			setTestResults((prev) => ({
				...prev,
				getChars: { success: false, error: error.message },
			}));
		}
	};

	const testGenerateSpaceContext = async () => {
		const testChars = characters.slice(0, 2).map((c) => c.name);
		try {
			const res = await axios.post(
				`${API}/context/generate-space-context`,
				{
					space_name: "Town Square",
					characters_present: testChars,
					available_objects: ["fountain", "bench", "notice_board"],
				}
			);
			setTestResults((prev) => ({
				...prev,
				spaceContext: { success: true, data: res.data },
			}));
		} catch (error) {
			setTestResults((prev) => ({
				...prev,
				spaceContext: { success: false, error: error.message },
			}));
		}
	};

	const testDecide = async () => {
		if (characters.length === 0) return;
		const char = characters[0];
		try {
			const characterLocations = characters.map((c) => ({
				character_name: c.name,
				space_name: characterPositions[c._id] || "Unknown",
			}));

			const res = await axios.post(
				`${API}/characters/${char._id}/decide`,
				{
					trigger_source: "test decision",
					space_states: [
						{
							space_name: "Secluded Garden",
							description: "",
							characters_present: characters
								.slice(0, 2)
								.map((c) => c.name),
							available_objects: [
								"flower_beds",
								"bench",
								"willow_tree",
							],
						},
						{
							space_name: "Town Tavern",
							description: "",
							characters_present: [],
							available_objects: [
								"bar_counter",
								"tables",
								"mugs",
							],
						},
					],
					global_context: {
						time: "afternoon",
						all_spaces: SPACES.map((s) => s.name),
						character_locations: characterLocations,
					},
				}
			);
			setTestResults((prev) => ({
				...prev,
				decide: { success: true, data: res.data },
			}));
		} catch (error) {
			setTestResults((prev) => ({
				...prev,
				decide: { success: false, error: error.message },
			}));
		}
	};

	const testAntonioResilience = async () => {
		const antonio = allCharacters.find(
			(c) => c.name === "Antonio Martinez"
		);
		if (!antonio) {
			setTestResults((prev) => ({
				...prev,
				resilience: {
					success: false,
					error: "Antonio Martinez not found",
				},
			}));
			return;
		}

		// Dummy space states with irrelevant changes
		const dummySpaceStates = [
			{
				space_name: "Town Square",
				description:
					"Some random people are walking around. Nothing special happening.",
				characters_present: ["Random Person 1", "Random Person 2"],
				available_objects: ["fountain", "bench"],
			},
			{
				space_name: "The Sleeping Dragon Inn",
				description: "The inn is quiet.",
				characters_present: [],
				available_objects: ["bar_counter", "tables"],
			},
		];

		try {
			const res = await axios.post(
				`${API}/characters/${antonio._id}/decide`,
				{
					trigger_source: "context change",
					space_states: dummySpaceStates,
					global_context: {
						time: "afternoon",
						weather: "sunny",
					},
				}
			);

			const action = res.data.action.actionType;
			const reasoning = res.data.reasoning;
			const isConservative = action === "continue" || action === "wait";

			setTestResults((prev) => ({
				...prev,
				resilience: {
					success: true,
					data: {
						action,
						reasoning,
						isConservative,
						message: isConservative
							? `✅ GOOD! Antonio chose "${action}" (being conservative)`
							: `⚠️ Antonio took action "${action}" on irrelevant trigger`,
					},
				},
			}));
		} catch (error) {
			setTestResults((prev) => ({
				...prev,
				resilience: { success: false, error: error.message },
			}));
		}
	};

	const testUseObject = async () => {
		if (characters.length === 0) return;
		const char = characters[0];
		try {
			const res = await axios.post(
				`${API}/characters/${char._id}/use/fountain`
			);
			setTestResults((prev) => ({
				...prev,
				useObject: { success: true, data: res.data },
			}));
		} catch (error) {
			setTestResults((prev) => ({
				...prev,
				useObject: { success: false, error: error.message },
			}));
		}
	};

	const testGetRelationships = async () => {
		if (characters.length === 0) return;
		const char = characters[0];
		try {
			const res = await axios.get(
				`${API}/relationships/character/${char._id}`
			);
			setTestResults((prev) => ({
				...prev,
				relationships: {
					success: true,
					count: res.data.length,
					data: res.data[0],
				},
			}));
		} catch (error) {
			setTestResults((prev) => ({
				...prev,
				relationships: { success: false, error: error.message },
			}));
		}
	};

	const testStartConversation = async () => {
		if (characters.length < 2) return;
		try {
			const res = await axios.post(`${API}/interaction-sessions/`, {
				character_ids: [characters[0]._id, characters[1]._id],
				interaction_type: "dialog",
			});
			setTestResults((prev) => ({
				...prev,
				startConvo: { success: true, data: res.data },
			}));
		} catch (error) {
			setTestResults((prev) => ({
				...prev,
				startConvo: { success: false, error: error.message },
			}));
		}
	};

	if (view === "testing") {
		return (
			<div className='app'>
				<div className='header'>
					<h1>🧪 API Endpoint Testing</h1>
					<button
						onClick={() => setView("simulation")}
						className='switch-view'
					>
						← Back to Simulation
					</button>
				</div>

				<div className='testing-grid'>
					{/* Test 1: Get Characters */}
					<div className='test-card'>
						<h3>1. GET /characters</h3>
						<p>Load all characters from database</p>
						<button onClick={testGetCharacters}>Test</button>
						{testResults.getChars && (
							<div
								className={`result ${
									testResults.getChars.success
										? "success"
										: "error"
								}`}
							>
								{testResults.getChars.success ? (
									<>
										<div>
											✅ Success! Loaded{" "}
											{testResults.getChars.count}{" "}
											characters
										</div>
										<pre>
											{JSON.stringify(
												testResults.getChars.data,
												null,
												2
											)}
										</pre>
									</>
								) : (
									<div>
										❌ Error: {testResults.getChars.error}
									</div>
								)}
							</div>
						)}
					</div>

					{/* Test 2: Generate Space Context */}
					<div className='test-card'>
						<h3>2. POST /context/generate-space-context</h3>
						<p>
							Unity sends space name + character names → Get AI
							description
						</p>
						<button
							onClick={testGenerateSpaceContext}
							disabled={characters.length < 2}
						>
							Test
						</button>
						{testResults.spaceContext && (
							<div
								className={`result ${
									testResults.spaceContext.success
										? "success"
										: "error"
								}`}
							>
								{testResults.spaceContext.success ? (
									<>
										<div>✅ Success!</div>
										<div>
											<strong>Space:</strong>{" "}
											{
												testResults.spaceContext.data
													.space_name
											}
										</div>
										<div>
											<strong>Description:</strong> "
											{
												testResults.spaceContext.data
													.description
											}
											"
										</div>
									</>
								) : (
									<div>
										❌ Error:{" "}
										{testResults.spaceContext.error}
									</div>
								)}
							</div>
						)}
					</div>

					{/* Test 3: Character Decision */}
					<div className='test-card'>
						<h3>3. POST /characters/{"{id}"}/decide</h3>
						<p>AI decides what character should do</p>
						<button
							onClick={testDecide}
							disabled={characters.length === 0}
						>
							Test with {characters[0]?.name}
						</button>
						{testResults.decide && (
							<div
								className={`result ${
									testResults.decide.success
										? "success"
										: "error"
								}`}
							>
								{testResults.decide.success ? (
									<>
										<div>✅ Success!</div>
										<div>
											<strong>Character:</strong>{" "}
											{
												testResults.decide.data
													.character_name
											}
										</div>
										<div>
											<strong>Reasoning:</strong>{" "}
											{testResults.decide.data.reasoning}
										</div>
										<div>
											<strong>Action:</strong>{" "}
											{
												testResults.decide.data.action
													.actionType
											}
										</div>
										<pre>
											{JSON.stringify(
												testResults.decide.data.action
													.props,
												null,
												2
											)}
										</pre>
										<div>
											<strong>State Changes:</strong>
										</div>
										<pre>
											{JSON.stringify(
												testResults.decide.data
													.state_changes,
												null,
												2
											)}
										</pre>
									</>
								) : (
									<div>
										❌ Error: {testResults.decide.error}
									</div>
								)}
							</div>
						)}
					</div>

					{/* Test 4: Use Object */}
					<div className='test-card'>
						<h3>
							4. POST /characters/{"{id}"}/use/{"{object}"}
						</h3>
						<p>
							Character interacts with object → Get emoji flavor
							text
						</p>
						<button
							onClick={testUseObject}
							disabled={characters.length === 0}
						>
							Test with {characters[0]?.name} using fountain
						</button>
						{testResults.useObject && (
							<div
								className={`result ${
									testResults.useObject.success
										? "success"
										: "error"
								}`}
							>
								{testResults.useObject.success ? (
									<>
										<div>✅ Success!</div>
										<div>
											<strong>Character:</strong>{" "}
											{
												testResults.useObject.data
													.character_name
											}
										</div>
										<div>
											<strong>Object:</strong>{" "}
											{
												testResults.useObject.data
													.object_name
											}
										</div>
										<div>
											<strong>Flavor Text:</strong> "
											{
												testResults.useObject.data
													.flavor_text
											}
											"
										</div>
									</>
								) : (
									<div>
										❌ Error: {testResults.useObject.error}
									</div>
								)}
							</div>
						)}
					</div>

					{/* Test 5: Get Relationships */}
					<div className='test-card'>
						<h3>5. GET /relationships/character/{"{id}"}</h3>
						<p>
							Get character's relationships with both perspectives
						</p>
						<button
							onClick={testGetRelationships}
							disabled={characters.length === 0}
						>
							Test with {characters[0]?.name}
						</button>
						{testResults.relationships && (
							<div
								className={`result ${
									testResults.relationships.success
										? "success"
										: "error"
								}`}
							>
								{testResults.relationships.success ? (
									<>
										<div>
											✅ Success! Found{" "}
											{testResults.relationships.count}{" "}
											relationships
										</div>
										<pre>
											{JSON.stringify(
												testResults.relationships.data,
												null,
												2
											)}
										</pre>
									</>
								) : (
									<div>
										❌ Error:{" "}
										{testResults.relationships.error}
									</div>
								)}
							</div>
						)}
					</div>

					{/* RESILIENCE TEST */}
					<div
						className='test-card'
						style={{ border: "2px solid #ff6b6b" }}
					>
						<h3>🧪 RESILIENCE: Antonio + Irrelevant Trigger</h3>
						<p>
							Test if Antonio ignores{" "}
							<strong>irrelevant "context change"</strong>{" "}
							triggers
							<br />
							(Should choose "continue" or "wait" ~90% of the
							time)
						</p>
						<button
							onClick={testAntonioResilience}
							disabled={allCharacters.length === 0}
							style={{
								backgroundColor: "#ff6b6b",
								color: "white",
								padding: "10px 20px",
							}}
						>
							Spam Antonio with Irrelevant Trigger
						</button>
						{testResults.resilience && (
							<div
								className={`result ${
									testResults.resilience.success
										? "success"
										: "error"
								}`}
							>
								{testResults.resilience.success ? (
									<>
										<div>✅ Success!</div>
										<div>
											<strong>Action:</strong>{" "}
											<code>
												{
													testResults.resilience.data
														.action
												}
											</code>
										</div>
										<div>
											<strong>Reasoning:</strong> "
											{
												testResults.resilience.data
													.reasoning
											}
											"
										</div>
										<div
											style={{
												color: testResults.resilience
													.data.isConservative
													? "#4caf50"
													: "#ff9800",
												fontWeight: "bold",
												marginTop: "10px",
												padding: "10px",
												backgroundColor: testResults
													.resilience.data
													.isConservative
													? "#e8f5e9"
													: "#fff3e0",
												borderRadius: "4px",
											}}
										>
											{
												testResults.resilience.data
													.message
											}
										</div>
									</>
								) : (
									<div>
										❌ Error: {testResults.resilience.error}
									</div>
								)}
							</div>
						)}
					</div>

					{/* Test 6: Start Conversation */}
					<div className='test-card'>
						<h3>6. POST /interaction-sessions/</h3>
						<p>Start AI conversation between 2 characters</p>
						<button
							onClick={testStartConversation}
							disabled={characters.length < 2}
						>
							Test: {characters[0]?.name} & {characters[1]?.name}
						</button>
						{testResults.startConvo && (
							<div
								className={`result ${
									testResults.startConvo.success
										? "success"
										: "error"
								}`}
							>
								{testResults.startConvo.success ? (
									<>
										<div>✅ Success! Session created</div>
										<div>
											<strong>Session ID:</strong>{" "}
											{testResults.startConvo.data._id}
										</div>
										<div>
											<strong>Participants:</strong>{" "}
											{testResults.startConvo.data.participant_names?.join(
												" & "
											)}
										</div>
										<div>
											<strong>Current Turn:</strong>{" "}
											{
												testResults.startConvo.data
													.current_turn
											}
										</div>
									</>
								) : (
									<div>
										❌ Error: {testResults.startConvo.error}
									</div>
								)}
							</div>
						)}
					</div>
				</div>
			</div>
		);
	}

	return (
		<div className='app'>
			<div className='header'>
				<h1>🎮 Unity Simulation - AI Life Sim</h1>
				<p>
					{characters.length} characters loaded • Testing Fight &
					Romance Actions
				</p>
				{activeConversations.some((c) => c.is_active) && (
					<p className='conversation-status'>
						💬 Active Conversation - Watch for 💬 dialogue, 👊
						fights, 💕 romance
					</p>
				)}
				<button
					onClick={() => setView("testing")}
					className='switch-view'
				>
					🧪 Test Endpoints
				</button>
			</div>

			<div className='controls'>
				<button onClick={nextTurn} className='next-turn'>
					▶️ Next Turn (.decide)
				</button>
				<button onClick={reset}>🔄 Reset</button>

				<div className='char-selector'>
					<label>Manual select:</label>
					<select
						value={selectedCharacter?._id || ""}
						onChange={(e) => {
							const char = characters.find(
								(c) => c._id === e.target.value
							);
							setSelectedCharacter(char);
						}}
					>
						<option value=''>Auto (first available)</option>
						{characters.map((c) => (
							<option key={c._id} value={c._id}>
								{c.name}
							</option>
						))}
					</select>
				</div>
			</div>

			<div className='main-content'>
				<div className='world-view'>
					<h2>🗺️ World State (Unity View)</h2>
					{SPACES.map((space) => {
						const charsHere = getCharactersInSpace(space.name);
						return (
							<div key={space.name} className='space-box'>
								<h3>{space.name}</h3>
								<div className='space-objects'>
									Objects: {space.objects.join(", ")}
								</div>
								<div className='characters-here'>
									{charsHere.map((char) => {
										const isTalking =
											activeConversations.some(
												(c) =>
													c.is_active &&
													c.participants?.includes(
														char._id
													)
											);
										return (
											<div
												key={char._id}
												className={`character-card ${
													isTalking ? "talking" : ""
												}`}
											>
												<div className='char-header'>
													<div className='char-name'>
														{char.name}
													</div>
													{isTalking && (
														<span className='talking-badge'>
															💬
														</span>
													)}
												</div>
												<div className='char-job'>
													{char.occupation}
												</div>
												<div className='char-traits'>
													{char.personality_traits
														?.slice(0, 3)
														.map((t, i) => (
															<span
																key={i}
																className='trait'
															>
																{t}
															</span>
														))}
												</div>
												<div className='char-desire'>
													💭{" "}
													{char.current_desire ||
														"No desire"}
												</div>
												<div className='char-needs'>
													<span>
														😊{" "}
														{char.needs?.happiness}
													</span>
													<span>
														⚡ {char.needs?.energy}
													</span>
												</div>
											</div>
										);
									})}
									{charsHere.length === 0 && (
										<div className='empty'>Empty</div>
									)}
								</div>
							</div>
						);
					})}
				</div>

				<div className='log-panel'>
					<h2>📜 Backend Activity Log</h2>
					<div className='log-content'>
						{logs
							.slice()
							.reverse()
							.map((log, i) => (
								<div
									key={i}
									className={`log-line ${
										log.highlight ? "highlight" : ""
									}`}
								>
									<span className='log-time'>{log.time}</span>
									<span className='log-msg'>
										{log.message}
									</span>
								</div>
							))}
						{logs.length === 0 && (
							<div className='empty'>
								Click Start to begin simulation...
							</div>
						)}
					</div>

					{activeConversations.filter((c) => c.is_active).length >
						0 && (
						<div className='active-convos'>
							<strong>Active Conversations:</strong>
							{activeConversations
								.filter((c) => c.is_active)
								.map((conv) => (
									<div key={conv._id} className='convo-badge'>
										{conv.participant_names?.join(" & ")} (
										{conv.messages?.length || 0} msgs)
									</div>
								))}
						</div>
					)}
				</div>
			</div>

			<div className='character-details'>
				<h3>👥 Character Details</h3>
				<div className='char-grid'>
					{characters.map((char) => (
						<div key={char._id} className='char-detail-card'>
							<div className='char-detail-header'>
								<strong>{char.name}</strong>
								<span className='location-badge'>
									{characterPositions[char._id]}
								</span>
							</div>
							<div className='char-detail-body'>
								<div>
									{char.age}yo {char.occupation}
								</div>
								<div className='detail-desire'>
									<strong>Desire:</strong>{" "}
									{char.current_desire || "None"}
								</div>
								<div className='detail-needs'>
									<span>😊 {char.needs?.happiness}</span>
									<span>⚡ {char.needs?.energy}</span>
									<span>🍖 {char.needs?.hunger}</span>
								</div>
							</div>
						</div>
					))}
				</div>
			</div>
		</div>
	);
}

export default App;
