# ADR-001: Clean Architecture and Domain-Driven Design Refactoring

## Status
Accepted

## Context
The prior architecture of ScripturesApp suffered from a high degree of coupling and blurred boundaries across layers. Specifically:
- **Domain Layer Anemia & Framework Leakage:** Domain entities (like `Verse` and `CrossReferenceRelation`) inherited directly from `pydantic.BaseModel`. This tied the entire core domain to a 3rd-party validation and HTTP serialization library, while the classes themselves contained no business logic.
- **The "Fat Service" Anti-pattern:** A monolithic `BibleService` class managed everything from database queries and string manipulation to invoking command-line subprocesses.
- **Leaky Infrastructure:** The application layer orchestrated direct `subprocess.run` executions for NLP python workers, making unit testing impossible without the entire heavy Spacy pipeline and local file structures present.

To scale the application robustly, it became strictly necessary to isolate the Domain, separate Use Cases, and abstract infrastructure calls behind generic Interfaces.

## Decision
We undertook a systemic refactoring following Clean Architecture and DDD principles:
1. **Pydantic Decoupling:** Migrated all `src/domain/models.py` definitions from Pydantic models to standard pure Python `@dataclass`. Explicit Pydantic DTOs were created in `src/api/dtos.py` strictly for the FastAPI delivery mechanism.
2. **Use Case Decomposition:** Dismantled `BibleService` into scoped, single-responsibility `Use Cases` (`SearchBibleUseCase`, `FindSeptantismsUseCase`, etc.) following the Command pattern.
3. **Ports and Adapters:** Abstracted all NLP interactions into an `NLPProvider` interface (Port) and implemented a `LocalNLPAdapter` that swallowed the OS subprocess logic. 
4. **Dependency Injection:** Created a structured `DependencyContainer` initialized at the application borders (`api/main.py` and `cli.py`) that wires concrete Adapters into the orchestrating Use Cases.

## Rationale
- **Testability:** By injecting dependencies (like `NLPProvider`) via object parameters, we mock external systems completely. The test suite no longer hangs on NLP execution.
- **Maintainability:** Standard Python dataclasses ensure our domain rules are completely isolated from future changes in the delivery mechanisms (e.g. if we migrated from FastAPI to another framework, or from Pydantic V1 to V2).
- **Scalability:** Wrapping the NLP process inside an Adapter allows us to eventually switch from a heavy local `subprocess` worker to an external remote microservice without changing any application or domain logic.

## Trade-offs
- **Increased Boilerplate:** We now have to manually map Python dataclasses to Pydantic DTOs at the edge of the API, which adds mapping logic that didn't exist when the models were shared.
- **Complexity in Instantiation:** Rather than just calling `BibleService()`, the CLI and API must now pass through a heavier Dependency Container sequence to initialize instances.
- **Loss of Implicit Casting:** Pydantic handled implicit type casting out of the box (e.g., converting incoming dictionary strings into Python `Enum` values). Pure dataclasses do not, requiring us to add explicit data casting inside Use Case mappers.

## Consequences
- **Positive:** We achieved 100% mocked unit test coverage spanning the application logic without hitting disk or launching OS processes. 
- **Positive:** Adding new NLP functionality or Database sources requires zero changes to existing Application Layer files.
- **Negative:** Slightly more convoluted setup inside the `pytest` initialization to swap DependencyContainer outputs.
- **Mitigation:** Wrote standardized pytest fixtures referencing the DI container configuration to streamline future test writing.
