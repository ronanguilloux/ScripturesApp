import SwiftUI

struct ContentView: View {
    @State private var selectedTab = 0
    @AppStorage("windowWidth_v2") private var windowWidth: Double = 600
    @AppStorage("windowHeight_v2") private var windowHeight: Double = 500
    @State private var dragStartSize: CGSize?

    var body: some View {
        ZStack(alignment: .bottomTrailing) {
            TabView(selection: $selectedTab) {
                ReadView()
                    .tabItem {
                        Label("Read", systemImage: "book")
                    }
                    .tag(0)
                
                FindView()
                    .tabItem {
                        Label("Find", systemImage: "character.book.closed")
                    }
                    .tag(1)
            }
            .frame(width: windowWidth, height: windowHeight)
            // .padding(.bottom, 20) // Only if needed for resize handle
            
            // Resize Handle
            Image(systemName: "arrow.down.forward")
                .font(.system(size: 14, weight: .bold))
                .foregroundColor(.secondary.opacity(0.5))
                .frame(width: 20, height: 20)
                .contentShape(Rectangle())
                .padding(2) // Bottom right padding
                .gesture(
                    DragGesture()
                        .onChanged { value in
                            if dragStartSize == nil {
                                dragStartSize = CGSize(width: windowWidth, height: windowHeight)
                            }
                            guard let start = dragStartSize else { return }
                            
                            windowWidth = max(320, start.width + value.translation.width)
                            windowHeight = max(300, start.height + value.translation.height)
                        }
                        .onEnded { _ in
                            dragStartSize = nil
                        }
                )
        }
    }
}
